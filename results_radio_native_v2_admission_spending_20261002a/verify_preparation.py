#!/usr/bin/env python3
"""Recheck this blocked snapshot; no source/control/native/telescope execution."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import mock

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO/'scripts'), str(REPO/'src')]
import radio_native_v2_compact_preparation_audit as audit
import radio_native_v2_activation_environment as environment

PLAN = REPO/'config/radio_native_v2_compact_eight_input_control_20261002m.plan.json'
FREEZE = REPO/'config/radio_native_v2_admission_spending_20261002a.runtime.json'


def verify():
    plan = audit.read_json(PLAN)
    freeze = audit.read_json(FREEZE)
    with tempfile.TemporaryDirectory(prefix='seti-custody-preparation-') as temporary:
        root = Path(temporary)
        code = root/'frozen-code'
        derived = root/'derived'
        for relative in audit.fixture.CODE_FILES:
            destination = code/relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((REPO/relative).read_bytes())
        derived.mkdir()
        for name, raw in audit.fixture.templates((REPO/audit.fixture.CODE_FILES[0]).read_text()).items():
            (derived/name).write_bytes(raw)
        result = audit.audit(plan, freeze, repo=REPO,
            materialized_code_root=code, derived_root=derived)
    # A post-activation custody check is pure file reading. Fail if it tries
    # either a process launch or alias inventory traversal.
    with mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('No Git/process allowed')):
        with mock.patch.object(audit.freezer.custody, 'bounded_inventory',
                side_effect=AssertionError('No activation alias scan allowed')):
            audit.freezer.validate_material_runtime_custody(freeze)
    exact_environment = environment.expected_environment(plan, freeze)
    argv = [plan['runtime_executables']['python']['path'], '-I', '-S', '-B',
        str(REPO/'scripts/radio_native_v2_activation_environment.py'),
        '--check-only', '--plan', str(PLAN), '--complete-freeze', str(FREEZE)]
    process = subprocess.run(argv, env=exact_environment, capture_output=True, timeout=30)
    if process.returncode or process.stderr:
        raise RuntimeError('Exact parent checker failed: '+process.stderr.decode('utf-8', 'replace'))
    parent = json.loads(process.stdout)
    if not parent['isolated_no_site_no_bytecode'] or not parent['bounded_activation_platform_contract_verified']:
        raise ValueError('Actual isolated parent/platform check required')
    assert len(exact_environment) == 10
    assert plan['execution_status'] == 'BLOCKED_PREPARATION_REVIEW'
    assert plan['spent_control_rearmed'] is False
    assert plan['source_worker_activation_receipt_delivery_complete'] is False
    assert plan['one_invocation_spending_enforced'] is False
    assert plan['source_worker_activation_receipt_delivery_prepared'] is True
    assert plan['durable_one_invocation_spending_prepared'] is True
    return {'schema':'radio-native-v2-admission-spending-preparation-preparation-verification-v1',
        'status':'PREPARATION_COHERENCE_VERIFIED_EXECUTION_BLOCKED',
        'audit':result, 'actual_parent_check':parent,
        'actual_parent_checker_argv':argv, 'actual_parent_environment_keys':sorted(exact_environment),
        'material_only_no_process_or_alias_scan_verified':True,
        'plan_file_pin':audit.pin(PLAN,sole_link=True),
        'freeze_file_pin':audit.pin(FREEZE,sole_link=True),
        'runtime_paths':len(freeze['runtime_file_inventory']),
        'hardlink_groups':len(freeze['runtime_custody_manifest']['hardlink_groups']),
        'activation_only_paths':len(freeze['runtime_custody_manifest']['activation_only_paths']),
        'material_runtime_paths':freeze['runtime_custody_manifest']['material_runtime_paths'],
        'hardlink_alias_closure_paths':freeze['runtime_custody_manifest']['hardlink_alias_closure_paths'],
        'material_code_files':len(plan['code_files']), 'derived_files':len(plan['derived_code']),
        'protected_control_invocations':0,'new_real_activation_markers_created':0,
        'large_inputs_generated':False,'scientific_cases_run':0,'rng_draws':0,
        'telescope_reads':0,'native_case_reservations':0,'native_case_executions':0,
        'external_person_messages_sent':0,'automatic_retry':False}


if __name__ == '__main__':
    print(json.dumps(verify(), sort_keys=True, separators=(',', ':'), allow_nan=False))
