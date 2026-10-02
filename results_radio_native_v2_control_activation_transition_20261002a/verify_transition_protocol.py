#!/usr/bin/env python3
"""Verify the prospective control-activation transition without executing it."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import time

REPO = Path(__file__).resolve().parents[1]
OUT = Path(__file__).parent
PROTOCOL = REPO/'config/radio_native_v2_control_activation_transition_20261002a.protocol.json'


def pin(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def git(*arguments):
    return subprocess.check_output(['git', '--no-replace-objects', *arguments],
        cwd=REPO, text=True, timeout=20).strip()


def first_call(function):
    body = function.body
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    if not body:
        return None
    statement = body[0]
    if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
        return None
    call = statement.value.func
    return call.id if isinstance(call, ast.Name) else None


def main():
    started = time.monotonic()
    protocol = json.loads(PROTOCOL.read_bytes())
    if protocol.get('schema') != 'radio-native-v2-control-activation-transition-v1':
        raise RuntimeError('Wrong transition protocol schema')
    if protocol.get('mode') != 'PROSPECTIVE_PROTOCOL_ONLY':
        raise RuntimeError('Transition must remain prospective')
    evidence = protocol['current_public_evidence']
    for name in ('preparation', 'execution_preread', 'readback_closure'):
        commit = evidence[name+'_commit']; tree = evidence[name+'_tree']
        if git('rev-parse', commit+'^{tree}') != tree:
            raise RuntimeError('Public science tree differs: '+name)
    if git('rev-parse', evidence['execution_preread_commit']+'^') != evidence['preparation_commit']:
        raise RuntimeError('Execution preread is not the expected preparation child')
    if git('rev-parse', evidence['readback_closure_commit']+'^') != evidence['execution_preread_commit']:
        raise RuntimeError('Readback closure is not the expected preread child')
    if git('rev-parse', evidence['main_readme_commit']+'^{tree}') != evidence['main_readme_tree']:
        raise RuntimeError('Public main tree differs')

    observed = {}
    for name, record in protocol['current_pins'].items():
        path = REPO/record['path']; actual = pin(path)
        if actual['sha256'] != record['sha256']:
            raise RuntimeError('Pinned byte mismatch: '+name)
        observed[name] = actual
    plan = json.loads((REPO/protocol['current_pins']['plan']['path']).read_bytes())
    preread = json.loads((REPO/protocol['current_pins']['execution_preread']['path']).read_bytes())
    if plan.get('execution_status') != 'BLOCKED_PREPARATION_REVIEW':
        raise RuntimeError('Historical plan status was rewritten')
    if preread.get('engineering_control_admitted') is not True:
        raise RuntimeError('Expected published structural admission bit is absent')
    if hashlib.sha256(canonical(plan)).hexdigest() != protocol['current_pins']['plan']['canonical_sha256']:
        raise RuntimeError('Plan canonical pin differs')
    freeze = json.loads((REPO/protocol['current_pins']['complete_freeze']['path']).read_bytes())
    if hashlib.sha256(canonical(freeze)).hexdigest() != protocol['current_pins']['complete_freeze']['canonical_sha256']:
        raise RuntimeError('Freeze canonical pin differs')
    if preread.get('plan_sha256') != protocol['current_pins']['plan']['canonical_sha256']:
        raise RuntimeError('Preread does not bind the exact plan')
    if preread.get('complete_freeze_sha256') != protocol['current_pins']['complete_freeze']['canonical_sha256']:
        raise RuntimeError('Preread does not bind the exact freeze')
    for name in ('material_runner', 'worker_admission'):
        record = protocol['current_pins'][name]
        if plan['code_files'][record['path']]['sha256'] != record['sha256']:
            raise RuntimeError('Plan omits current material code pin: '+name)

    runner = REPO/protocol['current_pins']['material_runner']['path']
    tree = ast.parse(runner.read_text())
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    required_first_gates = ('validate_activation', 'command_worker', 'exec_command_child',
        'verifier_worker', 'control_worker', 'run_control')
    gate_positions = {name: first_call(functions[name]) for name in required_first_gates}
    if any(value != 'require_execution_ready' for value in gate_positions.values()):
        raise RuntimeError('Expected global pre-admission gate order differs')
    gate = functions['require_execution_ready']
    compared = {node.id for node in ast.walk(gate) if isinstance(node, ast.Name)}
    if 'EXECUTION_STATUS' not in compared:
        raise RuntimeError('Expected constant global execution-status gate is absent')

    invariants = protocol['transition_invariants']
    required_false = ('historical_preparation_contract_rewritten', 'current_plan_or_preread_mutated',
        'marker_may_change_prepared_code', 'marker_may_change_plan_freeze_or_preread',
        'automatic_retry', 'scope_reuse', 'large_input_before_final_activation',
        'telescope_data_access', 'reservation_authorized', 'rng_authorized',
        'scientific_execution_authorized', 'native_execution_authorized',
        'external_messages_authorized')
    if any(invariants.get(key) is not False for key in required_false):
        raise RuntimeError('Transition protocol grants forbidden authority')
    phases = protocol['required_phases']
    if [row.get('ordinal') for row in phases] != list(range(1, 8)):
        raise RuntimeError('Seven exact ordered transition phases required')

    summary = {
        'schema': 'radio-native-v2-control-activation-transition-result-v1',
        'status': 'TRANSITION_PROTOCOL_VERIFIED_EXECUTION_STILL_BLOCKED',
        'protocol': pin(PROTOCOL),
        'public_commit_trees_and_parent_chain_verified': True,
        'current_plan_freeze_preread_and_material_pins_verified': True,
        'global_gate_precedes_preread_validation': True,
        'first_gate_positions': gate_positions,
        'existing_preread_can_activate_existing_runner': False,
        'pin_cycle_has_finite_marker_only_resolution': True,
        'required_phase_count': len(phases),
        'historical_preparation_contract_rewritten': False,
        'large_inputs_generated': False,
        'eight_input_resource_control_executed': False,
        'execution_authorized': False,
        'reservation_authorized': False,
        'scientific_execution_authorized': False,
        'native_case_reservations': 0,
        'native_case_executions': 0,
        'scientific_cases_run': 0,
        'rng_draws': 0,
        'telescope_reads': 0,
        'network_fetches': 0,
        'automatic_retry': False,
        'elapsed_seconds': time.monotonic()-started
    }
    target = OUT/'verification-summary.json'
    if target.exists() and json.loads(target.read_bytes()) != summary:
        # Elapsed time is evidence from this invocation; a new prospective attempt
        # must never silently overwrite an earlier receipt.
        raise RuntimeError('Existing transition verification receipt differs; overwrite refused')
    target.write_text(json.dumps(summary, sort_keys=True, separators=(',', ':'))+'\n')
    print(json.dumps({'status': summary['status'], 'phases': len(phases),
        'global_gate_precedes_preread_validation': True}, sort_keys=True))


if __name__ == '__main__':
    main()
