"""Build delivery metadata and a binary-only package from closed BI results.

No search, raw decoding, network or Library writes. Refuses partial processes,
unbound audit receipts and pre-existing delivery outputs.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work_bi'
OUT = WORK / 'results/run'
PREREG = '6f2258d01fdd5e6c4bb6490b3ced76f8dd63c6e6'
REPO = 'andersenmartin-blip/setisearch'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def verify_actual(path, result_path, plan_sha):
    actual = read(path)
    require(actual['actual_exit_code'] == 0 and actual['stdout_eof'] is True
            and actual['child_wait_completed'] is True, 'Closed actual0 receipt required')
    require(actual['plan_sha256'] == plan_sha and actual['prereg_github_commit'] == PREREG,
            'Actual plan/prereg binding differs')
    require(Path(actual['result_path']).resolve() == result_path.resolve()
            and actual['result_sha256'] == sha(result_path), 'Actual/result identity differs')
    log = Path(actual['log_path'])
    require(sha(log) == actual['log_sha256'] == actual['observed_stdout_sha256']
            and log.stat().st_size == actual['log_bytes'] == actual['observed_stdout_bytes'],
            'Observed stdout/log identity differs')
    return actual


def main():
    summary_path = WORK / 'results/REAL_SEARCH_SUMMARY_BI.json'
    resume_path = WORK / 'RESUME_BI.json'
    package_path = WORK / 'SETI_BI_SEARCH_RESULTS_2026-10-30.zip'
    metadata_path = WORK / 'results/BINARY_PACKAGE_BI.json'
    require(not any(p.exists() for p in (summary_path, resume_path, package_path, metadata_path)),
            'No delivery overwrite or automatic rebuild')
    plan_path = WORK / 'PLAN_BI.json'
    plan, plan_sha = read(plan_path), sha(plan_path)
    marker_path = OUT / 'ALL_FROZEN_Q_COMPLETE.json'
    complete = read(marker_path)
    require(complete['status'] == 'ALL_EIGHT_BOUNDED_Q_SEARCHES_AND_TRIAGE_COMPLETE'
            and complete['plan_sha256'] == plan_sha
            and complete['q_list'] == plan['core_q_list'] == list(range(17, 25)),
            'Complete frozen q17..24 results required')
    actual_path = WORK / 'execution/SEARCH_ACTUAL_EXIT_BI.json'
    actual = verify_actual(actual_path, marker_path, plan_sha)
    audit_path = WORK / 'review/REAL_RESULT_AUDIT_BI.json'
    audit_actual_path = WORK / 'review/REAL_RESULT_AUDIT_ACTUAL_EXIT_BI.json'
    audit = read(audit_path)
    audit_actual = verify_actual(audit_actual_path, audit_path, plan_sha)
    require(audit['status'] == 'PASS_CLOSED_BOUNDED_REAL_RESULTS'
            and audit['plan_sha256'] == plan_sha
            and audit['complete_result_sha256'] == sha(marker_path), 'Bound independent audit required')
    require(audit['audit_source_sha256'] == audit_actual['source_sha256']
            == sha(WORK / 'review/audit_real_results_bi.py'), 'Audit source identity differs')
    for path, digest in audit['input_and_artifact_sha256'].items():
        require(sha(path) == digest, 'Audited input/artifact changed: ' + path)
    for path, digest in plan['source_sha256'].items():
        require(sha(path) == digest, 'Frozen source changed: ' + path)
    require(actual['source_sha256'] == sha(WORK / 'bounded_search_bi.py'), 'Actual search source differs')

    scans = []
    per_band = []
    for q, combined in zip(plan['core_q_list'], complete['q_results']):
        directory = OUT / f'q{q:03d}'
        search, triage = read(directory / 'SIX_SCAN_SEARCH_COMPLETE.json'), read(directory / 'TRIAGE_RESULT.json')
        require(triage == combined and search['q'] == triage['q'] == q
                and search['plan_sha256'] == triage['plan_sha256'] == plan_sha,
                'Band result identity differs')
        for scope, inline in zip(plan['scans'], search['scans']):
            scan = read(directory / f'scan{scope["scan"]}_summary.json')
            require(scan == inline and scan['complete'] is True and scan['role'] == scope['role']
                    and scan['scan'] == scope['scan'], 'Saved scan summary differs')
            scans.append(scan)
        on_hits = sum(s['local_hits'] for s in search['scans'] if s['role'] == 'ON')
        require(on_hits == triage['ON_local_catalog_rows'], 'ON seed count differs')
        require(sum(s['track_trials'] for s in search['scans'])
                == search['track_trials'] == triage['search_track_trials'], 'Band trial count differs')
        per_band.append({'q': q, 'track_trials': search['track_trials'], 'ON_hits': on_hits,
                         'OFF_hits': sum(s['local_hits'] for s in search['scans'] if s['role'] == 'OFF'),
                         'forced_measurement_slots': triage['forced_measurement_slots'],
                         'forced_measurements': triage['supported_slots'],
                         'unsupported_forced_slots': triage['unsupported_slots'],
                         'any_OFF_ge5_rows': triage['any_OFF_ge5_rows'],
                         'all3ON_noOFF_flags': triage['all3ON_ge10_noOFF_rows']})
    require(len(scans) == len(plan['core_q_list']) * len(plan['scans']), 'Incomplete scan inventory')
    trials = sum(s['track_trials'] for s in scans)
    require(trials == complete['total_track_trials'] == audit['track_trials'], 'Total trial count differs')
    prior = read(ROOT / 'work_bh/results/REAL_SEARCH_SUMMARY_BH.json')
    previous = prior['cumulative_BG_BH']
    require(prior['q_list'] == list(range(9, 17))
            and previous['q_list'] == list(range(1, 17))
            and not set(previous['q_list']) & set(plan['core_q_list']),
            'Cumulative prior BG+BH bands must be completed and disjoint')
    bins = len(plan['core_q_list']) * plan['core_width_channels']
    df = plan['scans'][0]['df_hz']
    fch1 = plan['scans'][0]['fch1_mhz']
    on_hits = sum(s['local_hits'] for s in scans if s['role'] == 'ON')
    forced = sum(b['forced_measurements'] for b in per_band)
    limits = [
        'Descriptive local-q ESS calibration differs from historical full-native ESS; ESS is not calibrated significance.',
        'Correlated track trials are not independent statistical tests or new observational coverage.',
        ('Zero ON seeds means zero real forced ON/OFF measurements; empty source-consistency checks are vacuous.'
         if on_hits == 0 else
         'Forced ON/OFF measurements retain explicit support status; passing rows remain descriptive flags.'),
        'No calibrated FAP, astronomical sensitivity, origin, discovery or new-observation qualification.',
        'Independent audit samples selected scalar sums; shared kernel calibration replays do not independently qualify every trial, codec or full-native normalization.'
    ]
    maxima = {}
    for width in plan['widths_channels']:
        maxima[str(width)] = {
            role: max(w['maximum_local_ess'] for s in scans if s['role'] == role
                      for w in s['width_searches'] if w['width_channels'] == width)
            for role in ('ON', 'OFF')
        }
    rates = {w['drift_trials'] for s in scans for w in s['width_searches']}
    require(len(rates) == 1, 'Inconsistent drift grid count')
    cumulative_q = previous['q_list'] + plan['core_q_list']
    cumulative = {
        'q_list': cumulative_q,
        'scan_band_searches': previous['scan_band_searches'] + len(scans),
        'carrier_channels': previous['carrier_channels'] + bins,
        'technical_channel_bin_bandwidth_Hz': previous['technical_channel_bin_bandwidth_Hz'] + bins * abs(df),
        'total_correlated_track_trials_including_OFF': previous['total_correlated_track_trials_including_OFF'] + trials,
        'ON_catalog_hits_ge10': previous['ON_catalog_hits_ge10'] + on_hits,
        'OFF_catalog_hits_ge10': previous['OFF_catalog_hits_ge10'] + sum(s['local_hits'] for s in scans if s['role'] == 'OFF'),
        'real_forced_ON_OFF_measurements': previous['real_forced_ON_OFF_measurements'] + forced,
        'passing_flags': previous['passing_flags'] + sum(b['all3ON_noOFF_flags'] for b in per_band),
        'qualification': 'Disjoint carrier cores in one retained historical visit; no new observation or global original-search coverage credit.'
    }
    require(cumulative['total_correlated_track_trials_including_OFF'] == 1299013632
            and cumulative['technical_channel_bin_bandwidth_Hz'] == 274658.203125
            and cumulative['scan_band_searches'] == 144
            and cumulative['q_list'] == list(range(1, 25)),
            'Expected derived cumulative geometry differs')
    summary = {
        'schema': 'SETI_BI_REAL_SEARCH_SUMMARY_V1',
        'status': 'COMPLETED_REAL_BOUNDED_DESCRIPTIVE_SEARCH_AUDITED',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'target': plan['target'], 'observation_date': plan['observation_date'],
        'data_origin': 'Retained 2017 native171 archive; previously exposed data',
        'q_list': plan['core_q_list'], 'scan_count': len(plan['scans']), 'scan_band_searches': len(scans),
        'carrier_channels': bins, 'core_frequency_high_MHz': fch1 + min(plan['core_q_list']) * 4096 * df / 1e6,
        'core_frequency_low_MHz': fch1 + ((max(plan['core_q_list']) + 1) * 4096 - 1) * df / 1e6,
        'technical_channel_bin_bandwidth_Hz': bins * abs(df), 'width_channels': plan['widths_channels'],
        'drift_trials': rates.pop(), 'max_abs_drift_Hz_s': plan['max_abs_drift_hz_s'],
        'total_correlated_track_trials_including_OFF': trials, 'ON_catalog_hits_ge10': on_hits,
        'OFF_catalog_hits_ge10': sum(s['local_hits'] for s in scans if s['role'] == 'OFF'),
        'real_forced_ON_OFF_measurements': forced,
        'forced_measurement_slots': sum(b['forced_measurement_slots'] for b in per_band),
        'unsupported_forced_slots': sum(b['unsupported_forced_slots'] for b in per_band),
        'passing_flags': sum(b['all3ON_noOFF_flags'] for b in per_band),
        'maximum_local_ESS_by_width': maxima, 'per_band': per_band,
        'actual_search_exit_code': actual['actual_exit_code'], 'wall_seconds': actual['wall_seconds'],
        'user_cpu_seconds': actual['child_user_cpu_seconds'], 'max_RSS_KiB': actual['max_child_RSS_KiB'],
        'actual_receipt_sha256': sha(actual_path), 'independent_audit_sha256': sha(audit_path),
        'independent_audit_actual_exit_code': audit_actual['actual_exit_code'],
        'independent_scalar_sum_comparisons': audit['fixed_scalar_sum_comparisons'],
        'shared_kernel_calibration_vector_replays': audit['shared_kernel_calibration_vector_replays'],
        'independent_sampled_seed_count': audit['deterministic_sampled_ON_seeds'],
        'independent_sampled_forced_center_and_neighborhood_pairs': audit['forced_center_and_neighborhood_pairs_compared'],
        'source_prereg_commit': PREREG, 'new_archive_requests': 0, 'new_independent_observations': 0,
        'new_unique_archive_ID_credit': 0, 'global_technical_MHz_visit_counter_changed': False,
        'original_completed_authority_unchanged': prior['original_completed_authority_unchanged'],
        'cumulative_BG_BH_BI': cumulative, 'limits': limits
    }

    binaries = sorted(p for p in OUT.rglob('*') if p.is_file() and p.suffix in ('.npy', '.npz'))
    expected_binary_count = len(plan['scans']) * 2 + len(plan['core_q_list']) * (len(plan['scans']) * 3 + 1)
    require(len(binaries) == expected_binary_count == 164, 'Expected complete binary-only inventory')
    members = [{'member_name': str(p.relative_to(WORK)), 'bytes': p.stat().st_size, 'sha256': sha(p)}
               for p in binaries]
    bh_delivery = read(ROOT / 'work_bh/DELIVERY_BH.json')
    next_action = ('Continue the next fixed contiguous q25..32 in a new frozen source/plan before scores, '
                   'retaining exact numerical method and full-native normalization; preserve BG q1..8, BH q9..16 and BI q17..24. '
                   'No new Berkeley request or observation credit; never relabel exposed data as fresh. '
                   'Current BI support [65536,106496) is insufficient for the next batch; recompute full-native normalization from retained six H5 inputs. '
                   'No background science job remains after closed delivery.')
    resume = {
        'schema': 'SETI_BI_BINARY_RESULT_RESUME_V1', 'stage': 'BI', 'summary': summary,
        'binary_members': members, 'binary_member_count': len(members),
        'binary_payload_bytes': sum(m['bytes'] for m in members),
        'raw_input': bh_delivery['raw_input'],
        'prereg_github_commit': PREREG,
        'source_refs': {str(Path(p).relative_to(ROOT)): {'sha256': h, 'github_url': f'https://github.com/{REPO}/blob/{PREREG}/{Path(p).relative_to(ROOT)}'}
                        for p, h in plan['source_sha256'].items()},
        'plan_ref': {'path': 'work_bi/PLAN_BI.json', 'sha256': plan_sha,
                     'github_url': f'https://github.com/{REPO}/blob/{PREREG}/work_bi/PLAN_BI.json'},
        'text_results_location': 'GitHub science branch work_bi; actual receipts, JSON outputs, code and provenance remain in GitHub.',
        'previous_BG_results': bh_delivery['prior_BG_binary_results'],
        'previous_BH_results': bh_delivery['binary_results'],
        'next_action': next_action, 'next_q_list': list(range(25, 33)),
        'background_science_jobs_running': False,
        'contents': 'Binary normalized supports, full-native anchors, search grids, scalar audits, catalogs and forced ON/OFF arrays; no original raw data or code duplicated.'
    }
    write(summary_path, summary)
    write(resume_path, resume)
    with zipfile.ZipFile(package_path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for p, m in zip(binaries, members):
            archive.write(p, m['member_name'])
        archive.write(resume_path, 'RESUME_BI.json')
    with zipfile.ZipFile(package_path) as archive:
        require(archive.testzip() is None, 'ZIP CRC check failed')
        require(set(archive.namelist()) == {m['member_name'] for m in members} | {'RESUME_BI.json'}
                and len(archive.namelist()) == len(members) + 1, 'ZIP inventory differs')
        for m in members:
            data = archive.read(m['member_name'])
            require(len(data) == m['bytes'] and hashlib.sha256(data).hexdigest() == m['sha256'],
                    'ZIP binary identity differs: ' + m['member_name'])
        require(hashlib.sha256(archive.read('RESUME_BI.json')).hexdigest() == sha(resume_path), 'ZIP resume differs')
    metadata = {
        'schema': 'SETI_BI_BINARY_PACKAGE_VERIFICATION_V1',
        'status': 'ZIP_CRC_AND_EVERY_MEMBER_SHA256_VERIFIED_LOCAL_PENDING_LIBRARY_SAVE',
        'file_name': package_path.name, 'local_path': str(package_path),
        'bytes': package_path.stat().st_size, 'sha256': sha(package_path),
        'binary_members': len(members), 'archive_members': len(members) + 1,
        'binary_payload_bytes': sum(m['bytes'] for m in members),
        'resume_sha256': sha(resume_path), 'summary_sha256': sha(summary_path),
        'source_prereg_commit': PREREG, 'raw_data_or_code_duplicated': False,
        'next_action': next_action
    }
    write(metadata_path, metadata)
    print(json.dumps({'summary_path': str(summary_path), 'summary': summary,
                      'package_metadata_path': str(metadata_path), 'package': metadata}, indent=2))


if __name__ == '__main__':
    main()
