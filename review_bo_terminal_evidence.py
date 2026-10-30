"""Independent read/hash audit of closed BO outputs; never import experiment code."""
from pathlib import Path
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import stat
import sys

PLAN_SHA = 'cc04271a255bcf97c47450ccc267aa3d8df84e57c853315b8828227c77b2bfb5'
PUBLIC_COMMIT = 'a13cd82e917f5d4ebbfa4717dc171afc4e8e1d99'
IDS = ['E01', 'E02', 'E03', 'E04', 'E05']


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    path = Path(path)
    require(stat.S_ISREG(path.lstat().st_mode), 'Hash target is not regular: ' + str(path))
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def special(root):
    result = {}
    for path in sorted(Path(root).rglob('*')):
        info = path.lstat()
        if stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode):
            continue
        entry = {'lstat_mode': info.st_mode, 'lstat_size': info.st_size}
        if stat.S_ISLNK(info.st_mode):
            target = os.readlink(path)
            entry.update(type='symlink', target_text=target,
                         target_sha256=hashlib.sha256(os.fsencode(target)).hexdigest())
        elif stat.S_ISFIFO(info.st_mode):
            entry['type'] = 'fifo'
        else:
            entry['type'] = 'other_special'
        result[str(path.absolute())] = entry
    return result


def regular_paths(root):
    return {str(p.absolute()) for p in Path(root).rglob('*') if stat.S_ISREG(p.lstat().st_mode)}


def check_pins(pins):
    for path, digest in pins.items():
        require(sha(path) == digest, 'Pinned bytes changed: ' + path)


def capture_check(folder, expected_status='PASS', expected_exit=0, natural=True, caps=None):
    folder = Path(folder)
    receipt_path = folder / 'ACTUAL_RECEIPT.json'
    r = read(receipt_path)
    require(r['status'] == expected_status and r['actual_exit_code'] == expected_exit, 'Capture verdict/actual exit differs: ' + str(folder))
    require(r['child_wait_completed'] and r['stdout_eof'] and r['descendant_cleanup_completed']
            and not r['remaining_live_descendants'] and r['process_namespace_mapping_verified'], 'Unclosed child/pipe/descendants: ' + str(folder))
    require(r['natural_stdout_eof'] is natural, 'Natural EOF differs: ' + str(folder))
    require(r['stdout_fully_preserved'], 'Lost stdout: ' + str(folder))
    log = folder / 'STDOUT.log'
    require(sha(log) == r['log_sha256'] == r['observed_stdout_sha256']
            and log.stat().st_size == r['log_bytes'] == r['observed_stdout_bytes'], 'Observed/saved stdout differs: ' + str(folder))
    if expected_status == 'PASS':
        require(not r['killed'] and r['capture_error'] is None and not r['reasons']
                and r['source_pins_verified_before'] and r['source_pins_verified_after'], 'Invalid PASS capture: ' + str(folder))
        result_path = folder / 'payload/RESULT.json'
        require(sha(result_path) == r['result_sha256'], 'Result SHA differs')
        last = json.loads(log.read_text().splitlines()[-1])
        require(log.read_bytes().endswith(b'\n') and last == r['terminal_stdout_json']
                and last['event'] == 'GATE_TERMINAL_EOF' and last['status'] == 'PASS'
                and last['result_sha256'] == sha(result_path), 'Terminal/log/result binding differs')
        check_pins(r['source_pins']) if 'source_pins' in r else None
        if caps:
            v = r['resources']
            require(v['wall_seconds'] <= caps['wall_seconds'], 'Gate wall cap exceeded')
            require(v['capture_parent_cpu_seconds'] + v['child_user_cpu_seconds'] + v['child_system_cpu_seconds'] <= caps['cpu_seconds'], 'Gate total CPU cap exceeded')
            require(v['max_child_RSS_bytes'] <= caps['rss_bytes'] and v['peak_tree_RSS_bytes'] <= caps['rss_bytes'], 'Gate RSS cap exceeded')
            require(v['stored_bytes_total'] <= caps['stored_bytes'], 'Gate storage cap exceeded')
    return r


def audit(bo, actual_exit):
    plan_path = bo / 'BO_ENGINEERING_PLAN.json'
    require(sha(plan_path) == PLAN_SHA, 'Wrong frozen plan')
    plan = read(plan_path)
    require(plan['engineering_only'] and not any(plan[k] for k in ['real_telescope_powers_authorized', 'rng_authorized', 'scientific_scores_authorized']), 'Scope widened')
    require(plan['preserved_history']['HIP45688_M_raw_sum_failures'] == 24
            and plan['preserved_history']['HIP45688_M_full_QA'] is False
            and plan['preserved_history']['all_M_raw_sum_failures'] == 142, 'Historical failures changed')
    for pin in plan['source_pins']:
        p = bo / pin['path']
        require(p.stat().st_size == pin['bytes'] and sha(p) == pin['sha256'], 'Frozen source changed: ' + str(p))
    public_path = bo / 'PUBLIC_FREEZE_RECEIPT_BO.json'
    public = read(public_path)
    require(public['plan_sha256'] == PLAN_SHA and public['public_commit_sha'] == PUBLIC_COMMIT
            and public['exact_readback_verified'] and public['before_execution'] and public['verified_text_files'] == 22, 'Public freeze receipt differs')
    root = bo / plan['execution_relative_dir']
    markers = [p for p in [root / 'RUN_COMPLETE_BO.json', root / 'RUN_STOP_BO.json'] if p.is_file()]
    require(len(markers) == 1, 'Exactly one terminal marker required')
    marker_path = markers[0]
    marker_hash = sha(marker_path)
    marker = read(marker_path)
    actual_path = bo / 'review/OUTER_RUNNER_ACTUAL_EXIT_BO.json'
    outer = read(actual_path)
    require(outer['observed_process_completed'] and outer['actual_exit_code'] == actual_exit
            and outer['observed_completion_marker_sha256'] == marker_hash
            and outer['public_prereg_commit'] == PUBLIC_COMMIT, 'Actual runner exit witness differs')
    complete = marker_path.name == 'RUN_COMPLETE_BO.json'
    require((actual_exit == 0) is complete, 'Actual exit does not match COMPLETE/STOP')
    require(marker['plan_sha256'] == PLAN_SHA and marker['prereg_public_commit_sha'] == PUBLIC_COMMIT, 'Terminal prereg binding differs')
    require(marker['background_children_running'] is False and marker['cleanup_status'] == 'CLOSED_OR_NOT_STARTED', 'Terminal background closure unproved')
    require(marker['random_draws'] == marker['astronomical_powers_opened'] == marker['new_archive_requests'] == 0
            and marker['historical_M_failures_and_tolerances_unchanged']
            and not marker['statistical_sensitivity_recovery_or_FAP_qualified']
            and not marker['next_scientific_or_randomized_phase_activated'], 'Terminal scientific scope differs')
    check_pins(marker['source_and_runtime_pins'])
    artifacts = marker['output_artifact_sha256']
    require(regular_paths(root) == set(artifacts) | {str(marker_path)}, 'Terminal evidence set changed or contains unbound files')
    check_pins(artifacts)
    require(special(root) == marker['special_node_evidence'], 'Special-node map changed')
    expected_special = {
        str(root / 'E01/payload/fixtures/symlink.npy'): {'lstat_mode': stat.S_IFLNK | 0o777, 'lstat_size': 12, 'type': 'symlink', 'target_text': 'small_v1.npy', 'target_sha256': hashlib.sha256(b'small_v1.npy').hexdigest()},
        str(root / 'E01/payload/fixtures/nonblocking_fifo.npy'): {'lstat_mode': stat.S_IFIFO | 0o600, 'lstat_size': 0, 'type': 'fifo'}}
    require(set(special(root)) <= set(expected_special) and all(v == expected_special[k] for k, v in special(root).items()), 'Unexpected special node')
    completed = marker['gates_completed']
    require(completed == IDS[:len(completed)], 'Gate order/prefix differs')
    gate_results = {}
    receipts = []
    for gate in plan['gates'][:len(completed)]:
        g = gate['id']; folder = root / g
        r = capture_check(folder, caps=gate['caps']); receipts.append(r)
        start = read(folder / 'START.json')
        check_pins(start['source_pins'])
        require(start['caps'] == gate['caps'] and r['context']['gate_id'] == g and r['context']['plan_sha256'] == PLAN_SHA, 'Gate start/context differs')
        j = read(folder / 'payload/RESULT.json')
        require(j['gate'] == g and j['status'] == 'PASS', 'Wrong gate result')
        for key in ['plan_sha256', 'config_sha256']:
            if key in j: require(j[key] == PLAN_SHA, 'Gate plan pin differs')
        listed = next(x for x in marker['gate_receipts'] if x['gate_id'] == g)
        require(listed['sha256'] == sha(folder / 'ACTUAL_RECEIPT.json') and listed['status'] == 'PASS', 'Gate receipt marker binding differs')
        gate_results[g] = j
    for r in marker['per_gate_resources']:
        c = next(g['caps'] for g in plan['gates'] if g['id'] == r['gate_id'])
        require(r['wall_seconds'] <= c['wall_seconds'] and r['parent_and_child_cpu_seconds'] <= c['cpu_seconds'] and r['stored_bytes'] <= c['stored_bytes'], 'Actual gate cap exceeded')
    group = marker['deterministic_group_resources']; cap = plan['deterministic_group']
    require(group['wall_seconds'] <= cap['wall_seconds'] and group['total_cpu_seconds'] <= cap['cpu_seconds'] and group['stored_bytes'] <= cap['stored_bytes'], 'Shared cap exceeded')
    # Later terminal inventory is a different snapshot from earlier individual
    # receipts. Never equate their byte totals when extra artifacts are retained.
    final_group_bytes = sum(Path(p).stat().st_size for p in artifacts
                            if Path(p).is_relative_to(root/'E02')
                            or Path(p).is_relative_to(root/'E03')
                            or Path(p).is_relative_to(root/'E04'))
    require(final_group_bytes <= cap['stored_bytes'], 'Final bound group storage cap exceeded')
    noncanonical = [{'path': p, 'bytes': Path(p).stat().st_size, 'sha256': digest,
                     'classification': 'EXTRA_NONCANONICAL_COPY_ORIGIN_UNESTABLISHED',
                     'scientific_input_or_result_credit': False}
                    for p, digest in sorted(artifacts.items())
                    if Path(p).name.startswith('.') and '.npy.' in Path(p).name]
    summary = {'completed_gates': completed, 'runner_actual_exit_code': actual_exit,
               'terminal_status': marker['status'], 'run_wall_seconds': marker['total_run_wall_seconds'],
               'shared_E02_E04_resources': group}
    if complete:
        require(completed == IDS and marker['status'] == 'PASS_ALL_FIVE_ENGINEERING_GATES'
                and marker['reason'] is None and marker['source_and_runtime_reverified_after_last_gate'], 'Incomplete COMPLETE marker')
        require(special(root) == expected_special, 'E01 complete special evidence differs')
        e1 = gate_results['E01']; cases = e1['cases']
        require(e1['case_count'] == e1['passed_cases'] == len(cases) == 68 and e1['failed_cases'] == 0
                and all(c['pass'] and c['actual'] == c['expected'] for c in cases), 'E01 disposition differs')
        e2 = gate_results['E02']; require(e2['fixture_count'] == len(e2['fixtures']) == 2
            and len(e2['fatal_guard_checks']) == 6 and all(c['status'] == 'PASS_EXPECTED_REJECTION' for c in e2['fatal_guard_checks'])
            and e2['full_256_block_geometry_and_dtypes_verified'], 'E02 fixture/guard inventory differs')
        e2counts = {'anchors': 0, 'coefficients': 0, 'normalized_samples': 0}
        for d in e2['diagnostics']:
            o = d['oracle']; checks = o['checks']
            for c in checks:
                require(c['pass_'], 'E02 recorded oracle failed')
                if c['kind'] == 'INDEPENDENT_INTERPOLATION': require(0 <= c['absolute_error'] <= c['bound'], 'E02 coefficient bound failed')
                if c['kind'] == 'INDEPENDENT_NORMALIZED_SAMPLE': require(c['legacy_bit_exact'] and 0 <= c['current_absolute_error'] <= c['current_one_ULP_bound'], 'E02 sample oracle failed')
            e2counts['anchors'] += sum(c['kind'] == 'INDEPENDENT_ANCHOR' for c in checks)
            e2counts['coefficients'] += sum(c['kind'] == 'INDEPENDENT_INTERPOLATION' for c in checks)
            e2counts['normalized_samples'] += sum(c['kind'] == 'INDEPENDENT_NORMALIZED_SAMPLE' for c in checks)
        require(e2counts == {'anchors': 72, 'coefficients': 720, 'normalized_samples': 288}, 'E02 selected oracle counts differ')
        e3 = gate_results['E03']; points = e3['selected_checks']; require(len(points) == 1260, 'E03 count differs')
        ordinary = [p for p in points if not p['legacy_guard_failure_expected_from_frozen_cancellation_case']]
        cancellation = [p for p in points if p['legacy_guard_failure_expected_from_frozen_cancellation_case']]
        for p in points:
            error = abs(p['current_sum'] - p['current_fsum_reference'])
            bound = max(1e-8, 64 * 2.220446049250313e-16 * p['sum_abs_terms'])
            old_error = abs(p['legacy_sum'] - p['current_fsum_reference'])
            require(error == p['current_absolute_error'] and error <= bound == p['current_frozen_bound'], 'E03 current scalar summary inconsistent')
            require(p['legacy_sum'] == p['legacy_float32_oracle'] and p['legacy_float32_oracle_exact']
                    and old_error == p['legacy_error_against_fsum'], 'E03 legacy scalar summary inconsistent')
            require(p['legacy_original_5e_minus5_guard'] == ('PASS' if old_error <= 5e-5 else 'FAIL'), 'Legacy guard was relabelled')
        require(len(ordinary) == 1200 and len(cancellation) == 60
                and all(p['legacy_original_5e_minus5_guard'] == 'FAIL' and p['unguarded_float64_loss_observed']
                        and p['current_sum'] == p['expected_fsum'] == 8*p['width_channels'] for p in cancellation), 'E03 cancellation disposition differs')
        old_fails = sum(p['legacy_original_5e_minus5_guard'] == 'FAIL' for p in points)
        require(old_fails == e3['legacy_original_5e_minus5_guard_FAIL_count']
                and e3['historical_M_24_raw_sum_failures_preserved'] and e3['historical_M_full_QA_design_pass'] is False, 'Historical/engineering guard disposition differs')
        e4 = gate_results['E04']; require(e4['complete_local_oracle_checks'] == 800 and e4['complete_global_oracle_checks'] == 2
                and e4['factorial_records'] == 1600 and e4['support_rejection_count'] == 12
                and all(c['status'] == 'PASS_EXPECTED_SUPPORT_REJECTION' for c in e4['explicit_support_rejections']), 'E04 inventory differs')
        cal = read(root / 'E04/payload/INDEPENDENT_CALIBRATION_ORACLES.json')
        require(len(cal['checks']) == 802, 'Calibration reference count differs')
        for vector in cal['checks']:
            for c in vector['checks']:
                require(c['pass_'] and abs(c['actual'] - c['independent']) == c['absolute_error'] <= c['bound'], 'Calibration oracle summary inconsistent')
        factorial = read(root / 'E04/payload/FACTORIAL_DIAGNOSIS.json')['factorial_records']
        require(len(factorial) == 1600, 'Factorial record count differs')
        combinations = set()
        for p in factorial:
            combinations.add((p['fixture'], p['normalization'], p['accumulation'], p['calibration'], p['width'], p['rate_index'], p['q']))
            expected_domain = [4096,1044480] if p['calibration'] == 'global' else [p['q']*4096,(p['q']+1)*4096]
            require(p['calibration_domain'] == expected_domain and p['complete_calibration_carriers'] == (expected_domain[1]-expected_domain[0])//p['stride']
                    and p['MAD_scale'] > 0 and all(math.isfinite(x) for x in p['selected_ESS']), 'Calibration domain/summary invalid')
        require(len(combinations) == 1600, 'Factorial identities duplicate or missing')
        t = e4['time_and_support']; require(t['full_rate_bank_count'] == 839 and t['actual_offset_pairs_compared'] == 13424
            and t['maximum_shift_plus_radius'] < 4096 and t['fch1_slice_mhz'] == 1422.36328125, 'E04 time/support metadata differs')
        e5 = gate_results['E05']; require(e5['positive_captures'] == 1 and e5['expected_fault_rejections'] == 7 and len(e5['cases']) == 8, 'E05 contract count differs')
        expected_exits = {'valid':0,'nonzero':7,'timeout':-9,'truncated_stdout':0,'truncated_result':0,'missing_eof':0,'pin_change':0}
        for c in e5['cases']:
            mode = c['case']
            if mode == 'existing_output': require(c['reservation_refused'] and c['preexisting_bytes_unchanged'] and not c['child_started'], 'Existing-output fault not retained'); continue
            p = Path(c['receipt_path']); require(sha(p) == c['receipt_sha256'], 'Nested receipt pin changed')
            r = capture_check(p.parent, 'PASS' if mode == 'valid' else 'FAIL', expected_exits[mode], mode not in ['timeout','missing_eof'])
            if mode in ['timeout','missing_eof']: require(r['killed'] and any('WALL_' in x for x in r['reasons']), 'Deadline fault lacked cleanup')
            if mode.startswith('truncated'): require(any(x.startswith('TERMINAL_OR_RESULT_VALIDATION_FAILED') for x in r['reasons']), 'Truncation was not rejected')
            if mode == 'pin_change': require(r['source_pins_verified_before'] and not r['source_pins_verified_after'], 'Changed pin was not rejected')
        summary.update(E01_cases_passed=68,E02_independent_selected_oracles=e2counts,E02_fatal_rejections=6,
            E03_current_fsum_points=1260,E03_maximum_current_error=max(p['current_absolute_error'] for p in points),
            E03_fresh_legacy_guard_FAILs=old_fails,E03_ordinary_legacy_guard_FAILs=sum(p['legacy_original_5e_minus5_guard']=='FAIL' for p in ordinary),
            E03_cancellation_expected_FAILs=60,E03_maximum_legacy_error=max(p['legacy_error_against_fsum'] for p in points),
            E04_complete_local_oracles=800,E04_complete_global_oracles=2,E04_factorial_records=1600,E04_support_rejections=12,
            E05_positive_captures=1,E05_expected_fault_rejections=7)
    check_pins(artifacts)
    require(sha(marker_path) == marker_hash and read(marker_path) == marker
            and special(root) == marker['special_node_evidence'] and regular_paths(root) == set(artifacts)|{str(marker_path)}, 'Evidence/marker changed during audit')
    return {'schema':'SETI_BO_INDEPENDENT_TERMINAL_REVIEW_V1','status':'PASS_INDEPENDENT_CLOSED_EVIDENCE_REVIEW',
            'created_utc':datetime.now(timezone.utc).isoformat(),'runner_actual_exit_code':actual_exit,
            'outer_runner_actual_exit_receipt_sha256':sha(actual_path),'public_commit':PUBLIC_COMMIT,'plan_sha256':PLAN_SHA,
            'terminal_marker':str(marker_path),'terminal_marker_sha256':marker_hash,
            'regular_evidence_files_rehashed_twice':len(artifacts),'special_nodes_rechecked':len(special(root)),
            'frozen_source_files_rehashed':len(plan['source_pins']),'marker_and_evidence_maps_unchanged':True,
            'summary':summary,'original_M_failures_retained':{'HIP45688_raw_sum_failures':24,'HIP45688_full_QA':False,'all_M_raw_sum_failures':142},
            'extra_noncanonical_artifacts': noncanonical,
            'extra_artifact_note': 'Five randomized-suffix NPY copies were already included in the terminal map. Their origin is unestablished; workspace sync is only a hypothesis. They are preserved and hash-verified, never scientific inputs/results. Earlier process byte snapshots are not equated with later final inventories.',
            'final_bound_E02_E04_regular_bytes': final_group_bytes,
            'operations':{'experiment_imports':0,'RNG_draws':0,'astronomical_powers_opened':0,'new_scores':0,'gate_retries':0},
            'qualification':'Closed deterministic engineering evidence only. No paired synthetic recovery, astronomical input admission/search, FAP, sensitivity, physical origin, historical requalification or new coverage credit.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bo-root',type=Path,default=Path('/workspace/scratch/61f679f95cac/setisearch/work_bo'))
    parser.add_argument('--runner-exit-code',required=True,type=int)
    parser.add_argument('--out',type=Path)
    args = parser.parse_args()
    bo = args.bo_root.resolve(); out = args.out or bo/'review/TERMINAL_REVIEW_BO.json'
    try:
        report = audit(bo,args.runner_exit_code); code = 0
    except Exception as exc:
        report = {'schema':'SETI_BO_INDEPENDENT_TERMINAL_REVIEW_V1','status':'FAIL_INDEPENDENT_REVIEW',
                  'created_utc':datetime.now(timezone.utc).isoformat(),'reason':type(exc).__name__+': '+str(exc),
                  'no_gate_retry_or_numerical_mutation':True}; code = 1
    with out.open('x') as stream:
        json.dump(report,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
    print(json.dumps({'status':report['status'],'review_path':str(out),'review_sha256':sha(out),'summary':report.get('summary'),'reason':report.get('reason')},sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
