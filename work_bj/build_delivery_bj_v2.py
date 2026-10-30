"""Package the effective BJ V2 campaign and preserve the failed first batch10.

The caller supplies the immutable preregistration commit. Every included batch
must have a complete eight-band marker, closed actual search/audit receipts and
a passing bounded audit. No existing delivery file is overwritten.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work_bj'
REPO = 'andersenmartin-blip/setisearch'
WIDTHS = (1, 3, 9, 33)


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


class Evidence:
    def __init__(self):
        self.pins = {}

    def pin(self, path, expected=None):
        path = Path(path).resolve()
        digest = sha(path)
        require(expected is None or digest == expected, 'Evidence hash differs: ' + str(path))
        require(str(path) not in self.pins or self.pins[str(path)] == digest,
                'Conflicting evidence pin: ' + str(path))
        self.pins[str(path)] = digest
        return digest

    def actual(self, path, result, plan_sha, prereg):
        actual = read(path)
        self.pin(path)
        require(actual['actual_exit_code'] == 0 and actual['stdout_eof'] is True
                and actual['child_wait_completed'] is True, 'Closed actual0 receipt required')
        require(actual.get('capture_error') is None, 'Capture exception must remain explicit')
        require(actual['plan_sha256'] == plan_sha and actual['prereg_github_commit'] == prereg,
                'Actual plan/prereg binding differs')
        require(Path(actual['result_path']).resolve() == Path(result).resolve()
                and actual['result_sha256'] == self.pin(result), 'Actual/result identity differs')
        log = Path(actual['log_path'])
        require(self.pin(log) == actual['log_sha256'] == actual['observed_stdout_sha256']
                and log.stat().st_size == actual['log_bytes'] == actual['observed_stdout_bytes'],
                'Observed stdout/log identity differs')
        return actual


def collect_batch(inline, prereg, evidence):
    number = inline['batch']
    name = f'batch{number:02d}'
    out = Path(inline['complete_result_path']).resolve().parent
    require(out.is_relative_to(WORK / 'results'), 'Effective output must remain under BJ results')
    plan_path = WORK / 'plans' / f'{name}.json'
    plan = read(plan_path)
    ph = evidence.pin(plan_path)
    expected_q = list(range(25 + (number - 1) * 8, 33 + (number - 1) * 8))
    marker_path = out / 'ALL_FROZEN_Q_COMPLETE.json'
    marker = read(marker_path)
    require(marker['status'] == 'ALL_EIGHT_BOUNDED_Q_SEARCHES_AND_TRIAGE_COMPLETE'
            and marker['q_list'] == plan['core_q_list'] == expected_q
            and marker['plan_sha256'] == ph and len(marker['q_results']) == 8,
            'Complete frozen eight-band batch required: ' + name)
    actual_path = Path(inline['search_actual_path'])
    actual = evidence.actual(actual_path, marker_path, ph, prereg)
    audit_path = Path(inline['audit_result_path'])
    audit = read(audit_path)
    audit_actual_path = Path(inline['audit_actual_path'])
    audit_actual = evidence.actual(audit_actual_path, audit_path, ph, prereg)
    require(audit['status'] == 'PASS_CLOSED_BOUNDED_REAL_RESULTS'
            and audit['plan_sha256'] == ph
            and audit['complete_result_sha256'] == evidence.pin(marker_path),
            'Bound passing audit required: ' + name)
    require(audit['audit_source_sha256'] == audit_actual['source_sha256']
            == evidence.pin(WORK / 'review/audit_real_results_bj.py'), 'Audit source identity differs')
    for path, digest in audit['input_and_artifact_sha256'].items():
        # Reused raw inputs and source paths are pinned once across the campaign.
        if str(Path(path).resolve()) in evidence.pins:
            require(evidence.pins[str(Path(path).resolve())] == digest, 'Shared audited pin differs')
        else:
            evidence.pin(path, digest)
    for path, digest in plan['source_sha256'].items():
        evidence.pin(path, digest)
    require(actual['source_sha256'] == evidence.pin(WORK / 'bounded_search_bj.py'),
            'Actual search source differs')
    require(plan['previously_exposed_data'] is True and plan['new_independent_observation'] is False
            and plan['new_archive_requests_authorized'] == 0, 'Exposure/access scope differs')

    scans, bands = [], []
    for q, combined in zip(expected_q, marker['q_results']):
        directory = out / f'q{q:03d}'
        search_path = directory / 'SIX_SCAN_SEARCH_COMPLETE.json'
        triage_path = directory / 'TRIAGE_RESULT.json'
        search, triage = read(search_path), read(triage_path)
        evidence.pin(search_path)
        evidence.pin(triage_path)
        require(triage == combined and search['q'] == triage['q'] == q
                and search['plan_sha256'] == triage['plan_sha256'] == ph,
                'Saved band result identity differs')
        require(len(search['scans']) == len(plan['scans']) == 6, 'Six scans required')
        for scope, inline in zip(plan['scans'], search['scans']):
            sp = directory / f'scan{scope["scan"]}_summary.json'
            scan = read(sp)
            evidence.pin(sp)
            require(scan == inline and scan['complete'] is True
                    and scan['role'] == scope['role'] and scan['scan'] == scope['scan']
                    and scan['q'] == q, 'Saved scan summary differs')
            scans.append(scan)
        on_hits = sum(s['local_hits'] for s in search['scans'] if s['role'] == 'ON')
        require(on_hits == triage['ON_local_catalog_rows'], 'ON seed count differs')
        require(sum(s['track_trials'] for s in search['scans'])
                == search['track_trials'] == triage['search_track_trials'], 'Band trial count differs')
        bands.append({'batch': number, 'q': q, 'track_trials': search['track_trials'],
                      'ON_hits': on_hits,
                      'OFF_hits': sum(s['local_hits'] for s in search['scans'] if s['role'] == 'OFF'),
                      'forced_measurement_slots': triage['forced_measurement_slots'],
                      'forced_measurements': triage['supported_slots'],
                      'unsupported_forced_slots': triage['unsupported_slots'],
                      'any_OFF_ge5_rows': triage['any_OFF_ge5_rows'],
                      'all3ON_noOFF_flags': triage['all3ON_ge10_noOFF_rows']})
    trials = sum(s['track_trials'] for s in scans)
    require(len(scans) == 48 and trials == marker['total_track_trials']
            == audit['track_trials'] == 433004544, 'Complete batch geometry differs')
    require(audit['fixed_scalar_sum_comparisons'] == 1728
            and audit['shared_kernel_calibration_vector_replays'] == 576,
            'Expected finite audit counts differ')
    binaries = sorted(p for p in out.rglob('*') if p.is_file() and p.suffix in ('.npy', '.npz'))
    require(len(binaries) == 164, 'Complete batch binary inventory differs')
    record = {
        'batch': number, 'q_list': expected_q, 'scan_band_searches': len(scans),
        'effective_output_path': str(out.relative_to(ROOT)),
        'execution_prereg_github_commit': prereg,
        'total_correlated_track_trials_including_OFF': trials,
        'ON_catalog_hits_ge10': sum(b['ON_hits'] for b in bands),
        'OFF_catalog_hits_ge10': sum(b['OFF_hits'] for b in bands),
        'real_forced_ON_OFF_measurements': sum(b['forced_measurements'] for b in bands),
        'passing_flags': sum(b['all3ON_noOFF_flags'] for b in bands),
        'search_wall_seconds': actual['wall_seconds'],
        'search_user_cpu_seconds': actual['child_user_cpu_seconds'],
        'search_system_cpu_seconds': actual['child_system_cpu_seconds'],
        'audit_wall_seconds': audit_actual['wall_seconds'],
        'audit_user_cpu_seconds': audit_actual['child_user_cpu_seconds'],
        'audit_system_cpu_seconds': audit_actual['child_system_cpu_seconds'],
        'max_search_RSS_KiB': actual['max_child_RSS_KiB'],
        'actual_search_exit_code': actual['actual_exit_code'],
        'actual_audit_exit_code': audit_actual['actual_exit_code'],
        'independent_scalar_sum_comparisons': audit['fixed_scalar_sum_comparisons'],
        'shared_kernel_calibration_vector_replays': audit['shared_kernel_calibration_vector_replays'],
        'independent_sampled_ON_seeds': audit['deterministic_sampled_ON_seeds'],
        'independent_forced_pairs': audit['forced_center_and_neighborhood_pairs_compared'],
        'maximum_scalar_sum_error': audit['maximum_scalar_sum_error'],
        'maximum_replayed_calibration_error': audit['maximum_replayed_calibration_error'],
        'plan_path': str(plan_path.relative_to(ROOT)), 'plan_sha256': ph,
        'actual_receipt_path': str(actual_path.relative_to(ROOT)), 'actual_receipt_sha256': evidence.pin(actual_path),
        'audit_path': str(audit_path.relative_to(ROOT)), 'audit_sha256': evidence.pin(audit_path),
        'audit_actual_receipt_path': str(audit_actual_path.relative_to(ROOT)),
        'audit_actual_receipt_sha256': evidence.pin(audit_actual_path),
        'complete_result_sha256': evidence.pin(marker_path)
    }
    return plan, scans, bands, binaries, record


def collect_failed_first_batch10(campaign, original_prereg, evidence):
    """Preserve the current failed evidence without repairing its log or credit."""
    failure = campaign['superseded_original_batch10']
    stop_path = Path(campaign['original_stop_path'])
    evidence.pin(stop_path, campaign['original_stop_sha256'])
    stop = read(stop_path)
    require(stop['status'] == 'STOPPED_NO_NEXT_BATCH' and stop['completed_batches'] == 9,
            'Original nine-pass stop receipt differs')
    for stem in ('search_actual', 'audit_actual', 'complete_result', 'truncated_log', 'audit_log'):
        evidence.pin(failure[stem + '_path'], failure[stem + '_sha256'])
    actual = read(failure['search_actual_path'])
    audit_actual = read(failure['audit_actual_path'])
    complete = read(failure['complete_result_path'])
    require(actual['actual_exit_code'] == 0 and actual['stdout_eof'] is True
            and actual['child_wait_completed'] is True and actual['prereg_github_commit'] == original_prereg,
            'Original search actual0 closure differs')
    require(audit_actual['actual_exit_code'] == 1 and audit_actual['stdout_eof'] is True
            and audit_actual['child_wait_completed'] is True
            and audit_actual['prereg_github_commit'] == original_prereg,
            'Original failed audit actual1 closure differs')
    require(Path(actual['result_path']).resolve() == Path(failure['complete_result_path']).resolve()
            and actual['result_sha256'] == sha(failure['complete_result_path'])
            and complete['q_list'] == list(range(97, 105))
            and complete['total_track_trials'] == 433004544,
            'Original unqualified result marker binding differs')
    log = Path(failure['truncated_log_path'])
    require(log.resolve() == Path(actual['log_path']).resolve()
            and (sha(log) != actual['observed_stdout_sha256']
                 or log.stat().st_size != actual['observed_stdout_bytes']),
            'Original log discrepancy must remain explicit')
    require(actual['log_sha256'] == actual['observed_stdout_sha256']
            and actual['log_bytes'] == actual['observed_stdout_bytes'],
            'Original capture-time recorded log identity differs')
    out = Path(failure['complete_result_path']).resolve().parent
    binaries = sorted(p for p in out.rglob('*') if p.is_file() and p.suffix in ('.npy', '.npz'))
    require(len(binaries) == 164, 'Original failed binary retention inventory differs')
    record = {
        'status': 'ORIGINAL_BATCH10_FAILED_PROVENANCE_AUDIT_NOT_CREDITED',
        'batch': 10, 'q_list': list(range(97, 105)),
        'search_actual_exit_code': actual['actual_exit_code'],
        'audit_actual_exit_code': audit_actual['actual_exit_code'],
        'original_stop_path': str(stop_path.relative_to(ROOT)),
        'original_stop_sha256': sha(stop_path),
        'search_actual_path': str(Path(failure['search_actual_path']).relative_to(ROOT)),
        'search_actual_sha256': sha(failure['search_actual_path']),
        'audit_actual_path': str(Path(failure['audit_actual_path']).relative_to(ROOT)),
        'audit_actual_sha256': sha(failure['audit_actual_path']),
        'complete_result_path': str(Path(failure['complete_result_path']).relative_to(ROOT)),
        'complete_result_sha256': sha(failure['complete_result_path']),
        'truncated_log_path': str(log.relative_to(ROOT)),
        'current_saved_log_bytes': log.stat().st_size,
        'current_saved_log_sha256': sha(log),
        'capture_recorded_log_bytes': actual['observed_stdout_bytes'],
        'capture_recorded_log_sha256': actual['observed_stdout_sha256'],
        'failed_attempt_search_wall_seconds': actual['wall_seconds'],
        'failed_attempt_search_user_cpu_seconds': actual['child_user_cpu_seconds'],
        'failed_attempt_search_system_cpu_seconds': actual['child_system_cpu_seconds'],
        'failed_attempt_audit_wall_seconds': audit_actual['wall_seconds'],
        'failed_attempt_audit_user_cpu_seconds': audit_actual['child_user_cpu_seconds'],
        'failed_attempt_audit_system_cpu_seconds': audit_actual['child_system_cpu_seconds'],
        'unqualified_duplicate_track_combinations': complete['total_track_trials'],
        'qualified_track_credit': 0, 'retained_binary_members': len(binaries),
        'log_reconstructed_or_failure_overwritten': False,
        'qualification': 'Transport hashes preserve current failed-attempt bytes only; they do not turn the failed audit into a qualified null.'
    }
    return out, binaries, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prereg-commit', required=True)
    parser.add_argument('--recovery-commit', required=True)
    args = parser.parse_args()
    require(len(args.prereg_commit) == 40 and all(c in '0123456789abcdef' for c in args.prereg_commit),
            'Exact preregistration commit SHA required')
    require(len(args.recovery_commit) == 40 and all(c in '0123456789abcdef' for c in args.recovery_commit),
            'Exact recovery preregistration commit SHA required')
    summary_path = WORK / 'results/REAL_SEARCH_SUMMARY_BJ_V2.json'
    resume_path = WORK / 'RESUME_BJ_V2.json'
    package_path = WORK / 'SETI_BJ_SEARCH_RESULTS_V2_2026-10-30.zip'
    metadata_path = WORK / 'results/BINARY_PACKAGE_BJ_V2.json'
    require(not any(p.exists() for p in (summary_path, resume_path, package_path, metadata_path)),
            'No overwrite or automatic delivery rebuild')
    evidence = Evidence()
    campaign_path = WORK / 'results/CAMPAIGN_COMPLETE_BJ_V2.json'
    campaign = read(campaign_path)
    evidence.pin(campaign_path)
    require(campaign['schema'] == 'SETI_BJ_FINITE_CAMPAIGN_COMPLETION_V2'
            and campaign['status'] == 'ALL_TWELVE_BATCHES_SEARCHED_AND_AUDITED_WITH_TAIL_RECOVERY'
            and campaign['prereg_github_commit'] == args.prereg_commit
            and campaign['original_prereg_github_commit'] == args.prereg_commit
            and campaign['recovery_prereg_github_commit'] == args.recovery_commit
            and campaign['completed_batches'] == len(campaign['batch_results']) == 12
            and campaign['q_list'] == list(range(25, 121))
            and campaign['background_science_jobs_running'] is False,
            'Closed complete twelve-batch campaign receipt required')
    for path, digest in campaign['input_source_plan_sha256'].items():
        evidence.pin(path, digest)
    batches, scans, bands, binaries, plans = [], [], [], [], []
    for number, inline in enumerate(campaign['batch_results'], 1):
        require(inline['batch'] == number, 'Effective aggregate batch order differs')
        execution_prereg = args.prereg_commit if number <= 9 else args.recovery_commit
        plan, current_scans, current_bands, current_binaries, record = collect_batch(inline, execution_prereg, evidence)
        plans.append(plan)
        scans.extend(current_scans)
        bands.extend(current_bands)
        binaries.extend(current_binaries)
        batches.append(record)
        require(inline['batch'] == number and inline['q_list'] == record['q_list']
                and inline['search_actual_sha256'] == record['actual_receipt_sha256']
                and inline['audit_actual_sha256'] == record['audit_actual_receipt_sha256']
                and inline['audit_result_sha256'] == record['audit_sha256']
                and inline['complete_result_sha256'] == record['complete_result_sha256']
                and inline['ON_catalog_rows'] == record['ON_catalog_hits_ge10']
                and inline['passing_flags'] == record['passing_flags']
                and inline['total_track_trials'] == record['total_correlated_track_trials_including_OFF'],
                'Campaign aggregate/batch evidence differs')
    q_list = [b['q'] for b in bands]
    require(q_list == list(range(25, 121)) and len(scans) == 576, 'Exact twelve-batch campaign scope required')
    require(all(batches[i]['effective_output_path'].endswith(f'batch{i + 1:02d}/run') for i in range(9))
            and all(batches[i]['effective_output_path'].endswith(f'batch{i + 1:02d}_v2/run') for i in range(9, 12)),
            'Effective first-nine plus new-tail attempt paths differ')
    failed_out, failed_binaries, failed_attempt = collect_failed_first_batch10(campaign, args.prereg_commit, evidence)
    replay_out = Path(campaign['batch_results'][9]['complete_result_path']).resolve().parent
    replay_binaries = sorted(p for p in replay_out.rglob('*') if p.is_file() and p.suffix in ('.npy', '.npz'))
    original_map = {str(p.relative_to(failed_out)): evidence.pin(p) for p in failed_binaries}
    replay_map = {str(p.relative_to(replay_out)): evidence.pin(p) for p in replay_binaries}
    require(set(original_map) == set(replay_map) and len(original_map) == 164,
            'Original/replayed batch10 binary roles differ')
    differing = [{'relative_path': name, 'original_sha256': original_map[name],
                  'replayed_sha256': replay_map[name]} for name in sorted(original_map)
                 if original_map[name] != replay_map[name]]
    failed_attempt['original_vs_replayed_binary_sha256'] = {
        'compared_members': len(original_map), 'equal_members': len(original_map) - len(differing),
        'different_members': len(differing), 'differences': differing,
        'qualification': 'Measured byte identity comparison; the original failed log audit remains failed.'}
    reference = plans[0]
    for plan in plans:
        require(plan['scans'] == reference['scans'] and plan['widths_channels'] == list(WIDTHS)
                and plan['source_sha256'] == reference['source_sha256'], 'Campaign method/input family differs')
    prior_path = ROOT / 'work_bi/results/REAL_SEARCH_SUMMARY_BI.json'
    prior = read(prior_path)
    evidence.pin(prior_path)
    previous = prior['cumulative_BG_BH_BI']
    require(previous['q_list'] == list(range(1, 25)) and not set(previous['q_list']) & set(q_list),
            'Prior completed cores must be disjoint')
    prior_delivery = read(ROOT / 'work_bi/DELIVERY_BI.json')
    require(prior_delivery['summary_sha256'] == sha(prior_path), 'Prior delivery summary binding differs')
    df = reference['scans'][0]['df_hz']
    bins = len(q_list) * reference['core_width_channels']
    trials = sum(s['track_trials'] for s in scans)
    on_hits = sum(b['ON_hits'] for b in bands)
    off_hits = sum(b['OFF_hits'] for b in bands)
    forced = sum(b['forced_measurements'] for b in bands)
    flags = sum(b['all3ON_noOFF_flags'] for b in bands)
    cumulative = {
        'q_list': previous['q_list'] + q_list,
        'scan_band_searches': previous['scan_band_searches'] + len(scans),
        'carrier_channels': previous['carrier_channels'] + bins,
        'technical_channel_bin_bandwidth_Hz': previous['technical_channel_bin_bandwidth_Hz'] + bins * abs(df),
        'total_correlated_track_trials_including_OFF': previous['total_correlated_track_trials_including_OFF'] + trials,
        'ON_catalog_hits_ge10': previous['ON_catalog_hits_ge10'] + on_hits,
        'OFF_catalog_hits_ge10': previous['OFF_catalog_hits_ge10'] + off_hits,
        'real_forced_ON_OFF_measurements': previous['real_forced_ON_OFF_measurements'] + forced,
        'passing_flags': previous['passing_flags'] + flags,
        'qualification': 'Disjoint carrier cores of one retained historical visit; no new observation or original-search coverage credit.'
    }
    require(trials == campaign['total_track_trials'] == 5196054528
            and cumulative['total_correlated_track_trials_including_OFF'] == 6495068160
            and cumulative['technical_channel_bin_bandwidth_Hz'] == 1373291.015625
            and cumulative['q_list'] == list(range(1, 121)), 'Derived complete campaign geometry differs')
    maxima = {str(width): {role: max(w['maximum_local_ess'] for s in scans if s['role'] == role
                                   for w in s['width_searches'] if w['width_channels'] == width)
                           for role in ('ON', 'OFF')} for width in WIDTHS}
    rates = {w['drift_trials'] for s in scans for w in s['width_searches']}
    require(rates == {839}, 'Frozen drift grid count differs')
    limits = [
        'Descriptive local-q ESS differs from historical full-native ESS; ESS is not calibrated significance.',
        'Correlated track combinations are not independent statistical tests or new observational coverage.',
        ('Zero ON seeds means zero real forced ON/OFF measurements; empty source consistency checks are vacuous.'
         if on_hits == 0 else 'Forced ON/OFF measurements retain support status; passing rows are descriptive flags.'),
        'No calibrated FAP, astronomical sensitivity, physical origin, discovery or new-observation qualification.',
        'Independent selected scalar checks and shared-kernel calibration replays do not independently qualify every track, codec or normalization model.'
    ]
    summary = {
        'schema': 'SETI_BJ_REAL_SEARCH_SUMMARY_V2',
        'status': 'TWELVE_EFFECTIVE_REAL_BATCHES_AUDITED_WITH_PRESERVED_FAILED_FIRST_ATTEMPT',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'campaign_result_path': str(campaign_path.relative_to(ROOT)),
        'campaign_result_sha256': evidence.pin(campaign_path),
        'campaign_wall_seconds': campaign['wall_seconds'],
        'target': reference['target'], 'observation_date': reference['observation_date'],
        'data_origin': 'Retained 2017 native171 archive; previously exposed data',
        'q_list': q_list, 'completed_batches': len(batches), 'batch_results': batches,
        'scan_count': 6, 'scan_band_searches': len(scans), 'carrier_channels': bins,
        'technical_channel_bin_bandwidth_Hz': bins * abs(df),
        'core_frequency_high_MHz': reference['scans'][0]['fch1_mhz'] + min(q_list) * 4096 * df / 1e6,
        'core_frequency_low_MHz': reference['scans'][0]['fch1_mhz'] + ((max(q_list) + 1) * 4096 - 1) * df / 1e6,
        'width_channels': list(WIDTHS), 'drift_trials': 839, 'max_abs_drift_Hz_s': 4.0,
        'total_correlated_track_trials_including_OFF': trials,
        'ON_catalog_hits_ge10': on_hits, 'OFF_catalog_hits_ge10': off_hits,
        'real_forced_ON_OFF_measurements': forced,
        'forced_measurement_slots': sum(b['forced_measurement_slots'] for b in bands),
        'unsupported_forced_slots': sum(b['unsupported_forced_slots'] for b in bands),
        'passing_flags': flags, 'maximum_local_ESS_by_width': maxima, 'per_band': bands,
        'search_wall_seconds_sum': sum(b['search_wall_seconds'] for b in batches),
        'search_user_cpu_seconds_sum': sum(b['search_user_cpu_seconds'] for b in batches),
        'search_system_cpu_seconds_sum': sum(b['search_system_cpu_seconds'] for b in batches),
        'audit_wall_seconds_sum': sum(b['audit_wall_seconds'] for b in batches),
        'audit_user_cpu_seconds_sum': sum(b['audit_user_cpu_seconds'] for b in batches),
        'audit_system_cpu_seconds_sum': sum(b['audit_system_cpu_seconds'] for b in batches),
        'max_search_RSS_KiB': max(b['max_search_RSS_KiB'] for b in batches),
        'independent_scalar_sum_comparisons': sum(b['independent_scalar_sum_comparisons'] for b in batches),
        'shared_kernel_calibration_vector_replays': sum(b['shared_kernel_calibration_vector_replays'] for b in batches),
        'independent_sampled_ON_seeds': sum(b['independent_sampled_ON_seeds'] for b in batches),
        'independent_forced_pairs': sum(b['independent_forced_pairs'] for b in batches),
        'maximum_scalar_sum_error': max(b['maximum_scalar_sum_error'] for b in batches),
        'maximum_replayed_calibration_error': max(b['maximum_replayed_calibration_error'] for b in batches),
        'source_prereg_commit': args.prereg_commit, 'new_archive_requests': 0,
        'recovery_prereg_commit': args.recovery_commit,
        'preserved_failed_first_batch10': failed_attempt,
        'actual_search_attempt_count': len(batches) + 1,
        'actual_audit_attempt_count': len(batches) + 1,
        'failed_audit_attempt_count': 1,
        'total_attempt_search_wall_seconds_sum': sum(b['search_wall_seconds'] for b in batches)
            + failed_attempt['failed_attempt_search_wall_seconds'],
        'total_attempt_search_cpu_seconds_sum': sum(b['search_user_cpu_seconds'] + b['search_system_cpu_seconds'] for b in batches)
            + failed_attempt['failed_attempt_search_user_cpu_seconds'] + failed_attempt['failed_attempt_search_system_cpu_seconds'],
        'total_attempt_audit_wall_seconds_sum': sum(b['audit_wall_seconds'] for b in batches)
            + failed_attempt['failed_attempt_audit_wall_seconds'],
        'total_attempt_audit_cpu_seconds_sum': sum(b['audit_user_cpu_seconds'] + b['audit_system_cpu_seconds'] for b in batches)
            + failed_attempt['failed_attempt_audit_user_cpu_seconds'] + failed_attempt['failed_attempt_audit_system_cpu_seconds'],
        'new_independent_observations': 0, 'new_unique_archive_ID_credit': 0,
        'global_technical_MHz_visit_counter_changed': False,
        'original_completed_authority_unchanged': prior['original_completed_authority_unchanged'],
        'cumulative_BG_BH_BI_BJ': cumulative, 'limits': limits
    }
    require(len(binaries) == 1968 and len(set(binaries)) == len(binaries), 'Effective campaign binary inventory differs')
    effective_binaries = set(binaries)
    binaries = binaries + failed_binaries
    require(len(binaries) == 2132 and len(set(binaries)) == len(binaries), 'Effective plus failed retained inventory differs')
    members = [{'member_name': str(p.relative_to(WORK)), 'bytes': p.stat().st_size, 'sha256': evidence.pin(p),
                'attempt_qualification': 'EFFECTIVE_AUDITED_RESULT' if p in effective_binaries
                else 'FAILED_ORIGINAL_BATCH10_PROVENANCE_ATTEMPT_NOT_CREDITED'} for p in binaries]
    next_action = ('Freeze a new plan for q121..127, then explicitly skip protected native DC q128 before later safe cores. '
                   'Do not silently extend an eight-band contiguous batch across DC. Preserve BG q1..8, BH q9..16, BI q17..24 and BJ q25..120. '
                   'Recompute full-native normalization from the retained six H5 files for each new support window. '
                   'No new Berkeley requests, observation credit or fresh-data relabeling. No background science job remains after delivery.')
    resume = {
        'schema': 'SETI_BJ_BINARY_RESULT_RESUME_V2', 'stage': 'BJ_V2', 'summary': summary,
        'binary_members': members, 'binary_member_count': len(members),
        'binary_payload_bytes': sum(m['bytes'] for m in members),
        'raw_input': prior_delivery['raw_input'],
        'previous_BI_delivery_path': 'work_bi/DELIVERY_BI.json',
        'previous_BI_results': prior_delivery['binary_results'],
        'previous_BH_results': prior_delivery['prior_BH_binary_results'],
        'previous_BG_results': prior_delivery['prior_BG_binary_results'],
        'prereg_github_commit': args.prereg_commit,
        'recovery_prereg_github_commit': args.recovery_commit,
        'effective_binary_members': 1968, 'preserved_failed_binary_members': len(failed_binaries),
        'preserved_failed_first_batch10': failed_attempt,
        'campaign_result_path': str(campaign_path.relative_to(ROOT)),
        'campaign_result_sha256': evidence.pin(campaign_path),
        'source_refs': {str(Path(p).relative_to(ROOT)): {'sha256': h, 'github_url': f'https://github.com/{REPO}/blob/{args.prereg_commit}/{Path(p).relative_to(ROOT)}'}
                        for p, h in reference['source_sha256'].items()},
        'plan_refs': [{'path': b['plan_path'], 'sha256': b['plan_sha256'],
                       'github_url': f'https://github.com/{REPO}/blob/{args.prereg_commit}/{b["plan_path"]}'} for b in batches],
        'text_results_location': 'GitHub science branch work_bj; code, JSON results, actual receipts and provenance remain in GitHub.',
        'next_action': next_action, 'next_q_list': list(range(121, 128)), 'excluded_DC_q': 128,
        'background_science_jobs_running': False,
        'contents': '1968 effective audited binary results plus164 preserved original batch10 binaries with failed provenance audit, separately labeled; no original raw data or program code duplicated.'
    }
    # Recheck all distinct evidence before publication, including raw/source pins.
    for path, digest in evidence.pins.items():
        require(sha(path) == digest, 'Evidence changed during delivery build: ' + path)
    write(summary_path, summary)
    write(resume_path, resume)
    with zipfile.ZipFile(package_path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for p, member in zip(binaries, members):
            archive.write(p, member['member_name'])
        archive.write(resume_path, 'RESUME_BJ_V2.json')
    with zipfile.ZipFile(package_path) as archive:
        require(archive.testzip() is None, 'ZIP CRC check failed')
        require(set(archive.namelist()) == {m['member_name'] for m in members} | {'RESUME_BJ_V2.json'}
                and len(archive.namelist()) == len(members) + 1, 'ZIP inventory differs')
        for member in members:
            data = archive.read(member['member_name'])
            require(len(data) == member['bytes'] and hashlib.sha256(data).hexdigest() == member['sha256'],
                    'ZIP binary identity differs: ' + member['member_name'])
        require(hashlib.sha256(archive.read('RESUME_BJ_V2.json')).hexdigest() == sha(resume_path), 'ZIP resume differs')
    metadata = {
        'schema': 'SETI_BJ_BINARY_PACKAGE_VERIFICATION_V2',
        'status': 'ZIP_CRC_AND_EVERY_MEMBER_SHA256_VERIFIED_LOCAL_PENDING_LIBRARY_SAVE',
        'file_name': package_path.name, 'local_path': str(package_path),
        'bytes': package_path.stat().st_size, 'sha256': sha(package_path),
        'binary_members': len(members), 'archive_members': len(members) + 1,
        'effective_binary_members': 1968, 'preserved_failed_binary_members': len(failed_binaries),
        'binary_payload_bytes': sum(m['bytes'] for m in members),
        'resume_sha256': sha(resume_path), 'summary_sha256': sha(summary_path),
        'source_prereg_commit': args.prereg_commit, 'recovery_prereg_commit': args.recovery_commit,
        'raw_data_or_code_duplicated': False,
        'next_action': next_action
    }
    write(metadata_path, metadata)
    print(json.dumps({'summary_path': str(summary_path), 'completed_batches': len(batches),
                      'total_correlated_track_trials_including_OFF': trials,
                      'cumulative_correlated_track_trials_including_OFF': cumulative['total_correlated_track_trials_including_OFF'],
                      'package_metadata_path': str(metadata_path), 'package': metadata}, indent=2))


if __name__ == '__main__':
    main()
