"""One explicitly released BE numerical phase per invocation.

The numerical engine is unchanged. This wrapper never creates authorization
records. Each phase needs a new external, hash-bound GO and independent review.
Source import and --check do not execute a phase or open telescope arrays.
"""
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
from common_be import Context, LINEAGE, sha, read, new, require

BASE = Path(__file__).resolve().parents[2]
WORK = BASE / 'work_be'
ENGINE = WORK / 'science_root'
B = ENGINE / 'work_az'
PRODUCTION_SCOPE = 'COMPLETE_PRODUCTION_ACQUISITION_NATIVE_RECONSTRUCTION'


def validate_production_bound(protocol):
    require(protocol.get('execution_mode') == 'PRODUCTION',
            'Numerical execution requires production bound inputs; simulation/unknown/missing mode rejected')
    require(protocol.get('native_proof_scope') == PRODUCTION_SCOPE,
            'Numerical execution requires complete production acquisition/native reconstruction proof')
    return True


ACTIONS = ['scan_pool', 'triage', 'numeric_review', 'followup', 'followup_review',
           'main_figures', 'supplement_freeze', 'supplement', 'supplement_review',
           'supplement_figures', 'close']
PHASES = {
    'scan_pool': ('execution/SCAN_POOL_ACTUAL_EXIT_AZ.json', None, ['run_scan_pool_az.py']),
    'triage': ('execution/TRIAGE_ACTUAL_EXIT_AZ.json', None,
               ['detector/run_av.py', 'triage', '@bound', '@results']),
    'numeric_review': ('review/NUMERIC_ACTUAL_EXIT_AZ.json', 'review/INDEPENDENT_DETECTOR_AZ.json',
                       ['review/review_detector_az.py', '@bound', '@results', '--output',
                        'review/INDEPENDENT_DETECTOR_AZ.json', '--parent-go', '@legacy_go']),
    'followup': ('followup/FOLLOWUP_ACTUAL_EXIT_AZ.json', 'followup/results/FOLLOWUP_RESULT_AZ.json',
                 ['followup/followup_az.py', 'run', '--protocol', '@bound', '--results', '@results',
                  '--review', 'review/INDEPENDENT_DETECTOR_AZ.json', '--output', 'followup/results', '--parent-go']),
    'followup_review': ('followup/FOLLOWUP_REVIEW_ACTUAL_EXIT_AZ.json', 'followup/INDEPENDENT_FOLLOWUP_REVIEW_AZ.json',
                        ['followup/audit_followup_az.py', 'run', '--parent-go', '@legacy_go']),
    'main_figures': ('followup/PLOTS_ACTUAL_EXIT_AZ.json', 'followup/figures/FIGURE_MANIFEST_AZ.json',
                     ['followup/plot_context_az.py', 'followup/results/FOLLOWUP_RESULT_AZ.json', 'followup/figures']),
    'supplement_freeze': ('context_supplement/FREEZE_ACTUAL_EXIT_CONTEXT_SUPPLEMENT_AZ.json',
                          'context_supplement/PLAN_FROZEN_CONTEXT_SUPPLEMENT_AZ.json',
                          ['context_supplement/complete_context_supplement_az.py', 'freeze']),
    'supplement': ('context_supplement/ACTUAL_TOOL_CONTEXT_SUPPLEMENT_AZ.json',
                   'context_supplement/results/FOLLOWUP_RESULT_CONTEXT_SUPPLEMENT_AZ.json',
                   ['context_supplement/complete_context_supplement_az.py', 'run']),
    'supplement_review': ('context_supplement/INDEPENDENT_CONTEXT_SUPPLEMENT_ACTUAL_EXIT_AZ.json',
                          'context_supplement/review/INDEPENDENT_CONTEXT_SUPPLEMENT_REVIEW_AZ.json',
                          ['context_supplement/review/audit_context_supplement_az.py']),
    'supplement_figures': ('context_supplement/PLOTS_ACTUAL_EXIT_CONTEXT_SUPPLEMENT_AZ.json',
                           'context_supplement/figures/FIGURE_MANIFEST_CONTEXT_SUPPLEMENT_AZ.json',
                           ['context_supplement/plot_context_supplement_az.py'])}
REQUIRED_PRIOR = {
    'scan_pool': [], 'triage': ['scan_pool'], 'numeric_review': ['scan_pool', 'triage'],
    'followup': ['numeric_review'], 'followup_review': ['numeric_review', 'followup'],
    'main_figures': ['followup_review'], 'supplement_freeze': ['followup_review', 'main_figures'],
    'supplement': ['supplement_freeze'], 'supplement_review': ['supplement'],
    'supplement_figures': ['supplement_review'],
    'close': list(PHASES)}


def phase_binding_path(action):
    return WORK / ('SCIENCE_PHASE_' + action.upper() + '_BINDING_BE.json')


def verify_captured_phase(ctx, action, pins, bound, require_binding=True):
    receipt, result, _ = PHASES[action]
    actual_path = ctx.pin(B / receipt, pins)
    actual = read(actual_path)
    require(actual.get('actual_exit_code') == 0 and actual.get('child_actual_exit_code') == 0,
            'Captured numerical phase failed')
    for key in ['pipe_EOF_before_log_publish', 'parent_only_log_writer', 'log_flush_fsync_before_publish',
                'stream_file_byte_count_and_sha256_match']:
        require(actual.get(key) is True, 'Captured phase closure differs: ' + key)
    log = ctx.pin(actual['log'], pins, actual['log_sha256'])
    require(log.stat().st_size == actual['log_bytes'] == actual['stream_bytes_received'], 'Captured byte log differs')
    require(actual.get('automatic_retry') is False and actual.get('background_jobs_running') is False
            and actual.get('capture_failure') is None, 'Capture retry/failure state differs')
    if result:
        ctx.pin(B / result, pins, actual['result_sha256'])
    if action == 'scan_pool':
        pool_path = ctx.pin(B / 'execution/SCAN_POOL_EXECUTION_AZ.json', pins)
        pool = read(pool_path)
        require(pool['status'] == 'ALL_SIX_SCANS_CLOSED' and pool['protocol_sha256'] == sha(bound), 'Six-scan pool not closed')
        require(len(pool['exits']) == 6 and {x['scan'] for x in pool['exits']} == set(range(6))
                and all(x['exit_code'] == 0 for x in pool['exits']), 'Scan pool incomplete or failed')
    if require_binding:
        binding = read(ctx.pin(phase_binding_path(action), pins))
        require(binding['action'] == action and binding['protocol_sha256'] == sha(bound)
                and binding['actual_receipt_sha256'] == sha(actual_path), 'Prior phase binding differs')
        require(binding['sequencer_source_sha256'] == sha(__file__)
                and binding['outer_process_returncode'] == 0 and binding['outer_process_wait_completed'] is True,
                'Prior sequencer phase closure differs')
    return actual_path, actual


def verify(a):
    require(sys.flags.optimize == 0 and os.environ.get('PYTHONOPTIMIZE', '') in ('', '0'),
            'Unchanged numerical engine assertions require Python optimization disabled')
    ctx = Context(a.evidence_root, a.relocations)
    pins = {}
    bound = ctx.pin(B / 'PROTOCOL_BOUND_AZ.json', pins)
    protocol = read(bound)
    validate_production_bound(protocol)
    go_path = ctx.pin(a.go, pins)
    go = read(go_path)
    require(protocol['schema'] == 'SETI_BE_BOUND_UNCHANGED_FULLGRID_V1', 'Wrong bound protocol')
    require(protocol['recovery_input_lineage'] == LINEAGE, 'BB87+BC1+BE8 lineage differs')
    require(protocol['scientific_execution_authorized_by_binding'] is False, 'Binding must not self-release science')
    require(go.get('schema') == 'SETI_BE_SINGLE_PHASE_EXECUTION_GO_V1' and go.get('authorized') is True,
            'Separate phase execution GO required')
    require(go.get('action') == a.action and go.get('scientific_execution_authorized') is True,
            'GO does not authorize this exact phase')
    require(go.get('bound_protocol_sha256') == sha(bound) and go.get('sequencer_sha256') == sha(__file__),
            'GO protocol/sequencer binding differs')
    ctx.pin_relocations(go, pins)
    review_path = ctx.pin(go['independent_review_path'], pins, go['independent_review_sha256'])
    review = read(review_path)
    require(review.get('status') == 'PASS' and review.get('approved_action') == a.action
            and review.get('sequencer_sha256') == sha(__file__), 'Independent phase review missing or stale')
    prep_path = ctx.pin(WORK / 'SCIENCE_SOURCE_PREPARATION_BE.json', pins, go['source_preparation_sha256'])
    prep = read(prep_path)
    require(prep['status'] == 'PASS' and prep['numerical_sources_changed'] is False
            and len(prep['source_pairs']) == len({x['copied_path'] for x in prep['source_pairs']})
            == len({x['original_path'] for x in prep['source_pairs']}) == 33,
            'Unchanged original engine preparation required')
    for pair in prep['source_pairs']:
        require(pair['byte_identical'] is True, 'Changed numerical source')
        ctx.pin(pair['original_path'], pins, pair['sha256'])
        ctx.pin(pair['copied_path'], pins, pair['sha256'])
    for name, digest in protocol['source_sha256'].items():
        # Bound source keys include both engine-relative and absolute identities.
        path = Path(name) if Path(name).is_absolute() else ENGINE / name
        ctx.pin(path, pins, digest)
    for scope in protocol['scans']:
        ctx.pin(scope['native_path'], pins, scope['input_sha256'])
    release_path = ctx.pin(B / 'ROOT_DETECTOR_RELEASE_AZ.json', pins, go['detector_release_sha256'])
    release = read(release_path)
    require(release.get('authorized') is True and release.get('protocol_sha256') == sha(bound)
            and release.get('sequencer_sha256') == sha(__file__), 'Separate detector release required')
    require(release.get('binding_go_sha256') == protocol.get('binding_go_sha256'), 'Detector release binding GO differs')
    for name in REQUIRED_PRIOR[a.action]:
        verify_captured_phase(ctx, name, pins, bound)
    for path, digest in go['input_sha256'].items():
        ctx.pin(path, pins, digest)
    if a.action == 'numeric_review':
        legacy_go = ctx.pin(go['legacy_parent_go_path'], pins, go['legacy_parent_go_sha256'])
        require(read(legacy_go).get('root_after_triage') is True and read(legacy_go).get('authorized') is True,
                'Externally authorized numeric review gate required')
    elif a.action == 'followup_review':
        legacy_go = ctx.pin(go['legacy_parent_go_path'], pins, go['legacy_parent_go_sha256'])
        require(read(legacy_go).get('root_after_triage') is True and read(legacy_go).get('authorized') is True,
                'Externally authorized followup review gate required')
    else:
        legacy_go = None
    ctx.verify_pins(pins)
    return ctx, pins, bound, go_path, go, legacy_go


def expand_command(action, bound, legacy_go):
    literal = {'triage', 'run', 'freeze', '--output', '--parent-go', '--protocol', '--results', '--review'}
    expanded = []
    for word in PHASES[action][2]:
        if word == '@bound': expanded.append(str(bound))
        elif word == '@results': expanded.append(str(B / 'results'))
        elif word == '@legacy_go': expanded.append(str(legacy_go))
        elif word in literal: expanded.append(word)
        else: expanded.append(str(B / word))
    return [sys.executable, '-B', *expanded]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=ACTIONS)
    for name in ['go', 'evidence-root', 'relocations']:
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--check', action='store_true', help='Verify prerequisites; do not execute or write')
    a = parser.parse_args()
    ctx, pins, bound, go_path, go, legacy_go = verify(a)
    if a.check:
        print('PASS_BE_PHASE_PREREQUISITES_NO_EXECUTION ' + a.action)
        return
    started = WORK / ('SCIENCE_' + a.action.upper() + '_STARTED_BE.json')
    require(not started.exists(), 'No automatic phase restart')
    if a.action != 'close':
        receipt, result, _ = PHASES[a.action]
        require(not (B / receipt).exists() and (result is None or not (B / result).exists()),
                'Preserve old results; phase already entered')
    ctx.verify_pins(pins)
    new(started, {'started_utc': datetime.now(timezone.utc).isoformat(), 'action': a.action,
                  'bound_protocol_sha256': sha(bound), 'sequencer_sha256': sha(__file__),
                  'go_path': str(go_path), 'go_sha256': sha(go_path), 'no_implicit_retry': True})
    if a.action == 'close':
        new(WORK / 'SCIENCE_PHASES_CLOSED_BE.json', {
            'schema': 'SETI_BE_UNCHANGED_NUMERICAL_PHASES_CLOSED_V1',
            'status': 'CLOSED_VISUAL_AND_FINAL_AUDIT_PENDING',
            'completed_utc': datetime.now(timezone.utc).isoformat(), 'bound_protocol_sha256': sha(bound),
            'sequencer_sha256': sha(__file__), 'visual_review_pending': True,
            'final_recovery_aware_artifact_audit_pending': True, 'coverage_credit_added_by_this_runner': 0})
        return
    env = dict(os.environ, PYTHONPATH=str(WORK / 'runtime'))
    for key in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS']:
        env[key] = '1'
    runner = B / ('run_review_phase.py' if result else 'run_phase.py')
    args = [sys.executable, '-B', str(runner), 'BE_' + a.action.upper(), str(B / receipt)]
    if result: args.append(str(B / result))
    args += ['--', *expand_command(a.action, bound, legacy_go)]
    done = subprocess.run(args, env=env)
    require(done.returncode == 0, 'Numerical phase returned failure; no retry authorized')
    actual_path, actual = verify_captured_phase(ctx, a.action, pins, bound, require_binding=False)
    ctx.verify_pins(pins)
    new(phase_binding_path(a.action), {'schema': 'SETI_BE_CAPTURED_PHASE_BINDING_V1', 'action': a.action,
        'completed_utc': datetime.now(timezone.utc).isoformat(), 'protocol_sha256': sha(bound),
        'sequencer_source_sha256': sha(__file__), 'go_path': str(go_path), 'go_sha256': sha(go_path),
        'actual_receipt_path': str(actual_path), 'actual_receipt_sha256': sha(actual_path),
        'outer_process_returncode': done.returncode, 'outer_process_wait_completed': True,
        'inherited_capture_pipe_EOF_before_log_publish': actual['pipe_EOF_before_log_publish'],
        'inherited_capture_log_path': actual['log'], 'inherited_capture_log_sha256': actual['log_sha256'],
        'scope': 'Parent subprocess.run returned and waited. Inner source-pinned capture separately records pipeEOF/logfsync. Original capture receipt is unchanged.'})
    print(json.dumps({'status': 'PHASE_CLOSED', 'action': a.action, 'actual_exit_code': 0,
                      'coverage_credit_added': 0, 'visual_and_final_audit_still_required': True}))


if __name__ == '__main__':
    main()
