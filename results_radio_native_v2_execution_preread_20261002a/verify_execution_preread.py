#!/usr/bin/env python3
"""Build the distinct public preread from an exact public preparation commit."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
for folder in (REPO/'scripts', REPO/'src'):
    sys.path.insert(0, str(folder))
import radio_native_v2_compact_eight_case_resource_fixture as fixture
import radio_native_v2_worker_admission as admission

OUT = Path(__file__).parent
PLAN = REPO/'config/radio_native_v2_compact_eight_input_control_20261002i.plan.json'
FREEZE = REPO/'config/radio_native_v2_activation_environment_20261002c.runtime.json'
PREREAD = REPO/'config/radio_native_v2_execution_preread_20261002a.json'
PREPARATION_COMMIT = '39c8a4dee4f8c59357617e602855bea705217051'
PREPARATION_TREE = '08741f69c7574b00b8d2f9a9c619416790549699'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO, text=True,
        timeout=20).strip()


def main():
    started = time.monotonic()
    if git('rev-parse', PREPARATION_COMMIT+'^{tree}') != PREPARATION_TREE:
        raise RuntimeError('Public preparation commit tree differs from verified readback')
    for path in (PLAN, FREEZE):
        relative = str(path.relative_to(REPO))
        if git('rev-parse', PREPARATION_COMMIT+':'+relative) != git('hash-object', relative):
            raise RuntimeError('Public preparation blob differs: '+relative)
    plan = json.loads(PLAN.read_bytes()); freeze = json.loads(FREEZE.read_bytes())
    if plan != fixture.build_plan(REPO):
        raise RuntimeError('Current plan differs from public preparation plan')
    proof = {'schema': fixture.PREREAD_SCHEMA, 'namespace': fixture.NAMESPACE,
        'plan_sha256': hashlib.sha256(fixture.canonical(plan)).hexdigest(),
        'complete_freeze_sha256': hashlib.sha256(fixture.canonical(freeze)).hexdigest(),
        'public_immutable_readback_verified': True,
        'engineering_control_admitted': True,
        'code_files_verified': plan['code_files'],
        'preparation_commit': PREPARATION_COMMIT, **fixture.AUTHORITY}
    if PREREAD.exists():
        if json.loads(PREREAD.read_bytes()) != proof:
            raise RuntimeError('Existing preread differs; overwrite/retry refused')
    else:
        fixture.write(PREREAD, proof)
    validated = []
    for ordinal in range(8):
        bundle = admission.build_admission_bundle(plan, freeze, proof,
            execution_scope='/prospective/radio-native-v2-control-20261002a', ordinal=ordinal)
        layout = admission.worker_role_layout(bundle, ordinal=ordinal)
        validated.append({'ordinal': ordinal, 'source_case_id': plan['cases'][ordinal]['source_case_id'],
            'worker_scope': layout['worker_scope'],
            'bundle_sha256': hashlib.sha256(admission.bundle_bytes(bundle)).hexdigest()})
    negative_checks = []
    for label, mutate in (
            ('admission_false', lambda value: value.__setitem__('engineering_control_admitted', False)),
            ('changed_plan_pin', lambda value: value.__setitem__('plan_sha256', '0'*64))):
        changed = copy.deepcopy(proof); mutate(changed)
        try:
            admission.build_admission_bundle(plan, freeze, changed,
                execution_scope='/prospective/radio-native-v2-negative', ordinal=0)
        except ValueError as failure:
            negative_checks.append({'label': label, 'closed': True, 'error': str(failure)})
        else:
            raise RuntimeError('Mutated preread did not close: '+label)
    # The bundle format intentionally accepts any syntactically valid 40-hex
    # commit. Independent immutable readback, not a JSON label, authenticates it.
    wrong_commit = 'fd89f10550acc74a274bce7061667fb6e6397382'
    changed = copy.deepcopy(proof); changed['preparation_commit'] = wrong_commit
    admission.build_admission_bundle(plan, freeze, changed,
        execution_scope='/prospective/radio-native-v2-negative', ordinal=0)
    wrong_tree = git('rev-parse', wrong_commit+'^{tree}')
    if wrong_tree == PREPARATION_TREE:
        raise RuntimeError('Wrong preparation commit unexpectedly has the admitted tree')
    negative_checks.append({'label': 'wrong_preparation_commit', 'closed': True,
        'structural_bundle_check_alone_authenticates_remote_commit': False,
        'independent_public_tree_expected': PREPARATION_TREE,
        'independent_public_tree_observed': wrong_tree})
    summary = {'schema': 'radio-native-v2-execution-preread-result-v1',
        'status': 'DISTINCT_EXECUTION_PREREAD_STRUCTURALLY_VERIFIED_PUBLICATION_PENDING',
        'plan': fixture.pin(PLAN), 'complete_freeze': fixture.pin(FREEZE),
        'preread': fixture.pin(PREREAD),
        'public_preparation_commit': PREPARATION_COMMIT,
        'public_preparation_tree': PREPARATION_TREE,
        'public_preparation_plan_and_freeze_blobs_verified': True,
        'distinct_public_preread_structure_verified': True,
        'all_eight_worker_admission_identities_verified': True,
        'validated_identities': validated, 'negative_checks': negative_checks,
        'historical_preparation_contract_rewritten_to_ready': False,
        'plan_execution_status': plan['execution_status'],
        'activation_guard_complete': False,
        'execution_authorized': False, 'reservation_authorized': False,
        'scientific_execution_authorized': False,
        'large_source_generation_admitted': False, 'large_inputs_generated': False,
        'eight_input_resource_control_executed': False,
        'native_case_reservations': 0, 'native_case_executions': 0,
        'scientific_cases_run': 0, 'rng_draws': 0, 'telescope_reads': 0,
        'network_fetches': 0, 'actual_connector_calls': 0,
        'actual_functions_sdk_calls': 0, 'automatic_retry': False,
        'elapsed_seconds': time.monotonic()-started}
    fixture.write(OUT/'verification-summary.json', summary)
    print(json.dumps({'status': summary['status'], 'preread': summary['preread'],
        'identities': len(validated), 'negative_checks': len(negative_checks)}, sort_keys=True))


if __name__ == '__main__':
    main()
