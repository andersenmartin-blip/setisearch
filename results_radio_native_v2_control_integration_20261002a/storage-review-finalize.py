#!/usr/bin/env python3
"""Seal independent bounded probes after the root refreshes literal source pins.

Only result-directory review evidence and generated temporary probes are
written. Real journals, markers, protected controls and telescope files are
never dispatched by this script. Production code is only compiled by the pure
or tiny synthetic probe entrypoints already reviewed above.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys


BASE = Path(__file__).resolve().parent
REPO = BASE.parent


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def stable_read(path):
    first = path.read_bytes(); second = path.read_bytes()
    if first != second: raise ValueError('Source changed during review seal: '+str(path))
    return first


def exclusive(path, raw):
    with path.open('xb') as stream: stream.write(raw)


def semantic_digest(raw, allowed):
    tree = ast.parse(raw)
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            names = [target.id for target in statement.targets if isinstance(target, ast.Name)]
            if len(names) == 1 and names[0] in allowed:
                # Only a literal source-pin data assignment is ignored. Actual
                # implementation code and source names outside this declared
                # contract retain their full AST representation.
                ast.literal_eval(statement.value)
                statement.value = ast.Constant(value='<reviewed-literal-pin-refresh>')
    return hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest()


specs = {
    'resource_finalization': ('storage-review-current-finalizer-source.py', {'BOOTSTRAP_SOURCE_PINS'}),
    'historical_observation': ('storage-review-initial-historical_observation-source.py', set()),
    'historical_storage': ('storage-review-initial-historical_storage-source.py', set()),
    'compact_eight_case_resource_fixture': ('storage-review-reviewed-compact_eight_case_resource_fixture-held-plan-source.py',
        {'WORKER_ADMISSION_IMPLEMENTATION_PIN', 'CONTROL_ACTIVATION_IMPLEMENTATION_PIN',
         'INVOCATION_SPENDING_IMPLEMENTATION_PIN', 'HISTORICAL_OBSERVATION_IMPLEMENTATION_PIN',
         'ACTIVATION_ENVIRONMENT_IMPLEMENTATION_PIN'}),
    'compact_control_launch': ('storage-review-reviewed-compact_control_launch-source.py', {'BOOTSTRAP_SOURCE_PINS'}),
    'worker_admission': ('storage-review-reviewed-worker_admission-history-first-source.py', {'SPENDING_IMPLEMENTATION_PIN'}),
    'process_tree_supervisor': ('storage-review-reviewed-process_tree_supervisor-quota-source.py', {'BOOTSTRAP_SOURCE_PINS'}),
    'control_activation': ('storage-review-reviewed-control_activation-source.py', set()),
}
sources = {}; held_paths = {}; raw_sources = {}
for name, (reviewed_file, allowed) in specs.items():
    relative = 'scripts/radio_native_v2_'+name+'.py'
    raw = stable_read(REPO/relative); reviewed = stable_read(BASE/reviewed_file)
    before = semantic_digest(reviewed, allowed); after = semantic_digest(raw, allowed)
    if before != after:
        raise ValueError('Implementation changed beyond reviewed literal pin assignments: '+relative)
    held = BASE/('storage-review-final-'+name+'-source.py')
    held_paths[name] = held; raw_sources[name] = raw
    sources[relative] = {'reviewed_pin': pin(reviewed), 'final_pin': pin(raw),
        'semantic_sha256': after, 'ignored_literal_pin_assignments': sorted(allowed),
        'retained_final_source': held.name}

# Verify all refreshed pin values against actual exact bytes without executing
# the source that defines them. Literal map labels provide no self-authentication.
refreshed = {}
fixture_names = {
    'WORKER_ADMISSION_IMPLEMENTATION_PIN': 'scripts/radio_native_v2_worker_admission.py',
    'CONTROL_ACTIVATION_IMPLEMENTATION_PIN': 'scripts/radio_native_v2_control_activation.py',
    'INVOCATION_SPENDING_IMPLEMENTATION_PIN': 'scripts/radio_native_v2_prospective_spending.py',
    'HISTORICAL_OBSERVATION_IMPLEMENTATION_PIN': 'scripts/radio_native_v2_historical_observation.py',
    'ACTIVATION_ENVIRONMENT_IMPLEMENTATION_PIN': 'scripts/radio_native_v2_activation_environment.py'}
for name in ('resource_finalization', 'process_tree_supervisor', 'compact_control_launch', 'compact_eight_case_resource_fixture'):
    tree = ast.parse(raw_sources[name]); selected = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name): continue
        key = statement.targets[0].id
        if key == 'BOOTSTRAP_SOURCE_PINS': selected.update(ast.literal_eval(statement.value))
        elif name == 'compact_eight_case_resource_fixture' and key in fixture_names:
            selected[fixture_names[key]] = ast.literal_eval(statement.value)
    if not selected: raise ValueError('Expected literal source-pin contract absent: '+name)
    for relative, expected in selected.items():
        if expected != pin(stable_read(REPO/relative)):
            raise ValueError('Refreshed literal source pin differs from actual bytes: '+name+' -> '+relative)
    refreshed[name] = selected
worker_tree = ast.parse(raw_sources['worker_admission'])
worker_spending_pin = next(ast.literal_eval(statement.value) for statement in worker_tree.body
    if isinstance(statement, ast.Assign) and len(statement.targets) == 1
    and isinstance(statement.targets[0], ast.Name)
    and statement.targets[0].id == 'SPENDING_IMPLEMENTATION_PIN')
if worker_spending_pin != pin(stable_read(REPO/'scripts/radio_native_v2_prospective_spending.py')):
    raise ValueError('Refreshed worker prospective spending literal differs from actual exact bytes')
refreshed['worker_admission'] = {'scripts/radio_native_v2_prospective_spending.py': worker_spending_pin}
if 'scripts/radio_native_v2_invocation_spending.py' in refreshed['compact_control_launch']:
    raise ValueError('Launcher must select prospective c spending bootstrap')
if 'scripts/radio_native_v2_prospective_spending.py' not in refreshed['compact_control_launch']:
    raise ValueError('Launcher prospective c spending bootstrap absent')

# All semantic and literal closure checks above precede the first exclusive
# review write. Refuse a previously used final path before writing any of them.
final_paths = [*held_paths.values(), BASE/'storage-review-final-review.json']
labels = ('general-join', 'nofollow', 'root-contract', 'current-mutation', 'sampled-named-metadata', 'held-plan-selection')
final_paths.extend(BASE/('storage-review-final-'+label+'-result.json') for label in labels)
if any(path.exists() for path in final_paths):
    raise ValueError('Distinct final review paths already used; retained evidence will not be overwritten')
for name, held in held_paths.items(): exclusive(held, raw_sources[name])

runs = (
    ('general-join', 'storage-review-general-join-probe.py', held_paths['resource_finalization']),
    ('nofollow', 'storage-review-nofollow-probe.py', held_paths['historical_observation']),
    ('root-contract', 'storage-review-root-contract-probe.py', held_paths['historical_observation']),
    ('current-mutation', 'storage-review-current-caller-mutation-probe.py', held_paths['resource_finalization']),
    ('sampled-named-metadata', 'storage-review-sampled-named-metadata-probe.py', held_paths['process_tree_supervisor']),
    ('held-plan-selection', 'storage-review-held-plan-selection-probe.py', held_paths['compact_eight_case_resource_fixture']),
)
results = {}; count = 0
for label, runner, held in runs:
    completed = subprocess.run([sys.executable, '-I', '-S', '-B', str(BASE/runner), str(held)],
        cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30)
    if completed.returncode or completed.stderr:
        raise ValueError('Bounded review probe failed: '+label+' '+completed.stderr.decode())
    value = json.loads(completed.stdout)
    passed = value.get('all_expectations_met', value.get('result', {}).get('snapshot_preserved'))
    if passed is not True: raise ValueError('Final candidate probe expectation failed: '+label)
    destination = BASE/('storage-review-final-'+label+'-result.json')
    exclusive(destination, completed.stdout)
    n = len(value.get('cases', [value['result']] if 'result' in value else []))
    count += n
    results[label] = {'path': destination.name, 'raw_pin': pin(completed.stdout),
                     'runner': runner, 'runner_pin': pin(stable_read(BASE/runner)), 'checks': n}

report = {
    'schema': 'radio-native-v2-independent-storage-integration-review-v1',
    'status': 'FINAL_REVIEWED_SOURCE_PINS_AND_BOUNDED_PROBES_PASSED_EXECUTION_BLOCKED',
    'reviewer_kind': 'independent_machine_agent', 'human_review': False,
    'review_scope': ['external three-component exact storage allocation and caps',
        'current workload duplicate paths/inodes and external root ancestry',
        'historical copied-input raw pins, held source bootstrap and original root',
        'nofollow file/ancestor mutation behavior using generated tiny fixtures',
        'c reobservation on both sides of historical traversal and finalizer lifetime call sites'],
    'sources': sources, 'refreshed_literal_pin_contracts': refreshed,
    'probe_results': results, 'final_candidate_bounded_checks_passed': count,
    'resolved_findings': [{
        'finding': 'Current caller inventory could be altered after validation and before allocation.',
        'original_source_pin': pin(stable_read(BASE/'storage-review-original-finalizer-source.py')),
        'reproduction': 'storage-review-original-current-mutation-result.json',
        'original_synthetic_result': '512 validated logical/allocated bytes became 0 after caller mutation.',
        'repair': 'Canonical bounded detached current snapshot is now validated and allocated.',
        'fixed_reproduction': 'storage-review-final-current-mutation-result.json',
        'fixed_synthetic_result': 'The same scheduled caller mutation retains 512 logical/allocated bytes.',
        'probe_limit': 'Pure in-process mutation scheduling hook; no filesystem exploit or actual control was run.'}, {
        'finding': 'Workload check selected its finalizer using a second unauthenticated plan.json read after authenticating joined storage.',
        'original_source_pin': pin(stable_read(BASE/'storage-review-reviewed-compact_eight_case_resource_fixture-quota-source.py')),
        'reproduction': 'storage-review-original-held-plan-selection-result.json',
        'original_synthetic_result': 'Authenticated held join was allocated with the unchecked second-read plan.',
        'repair': 'The authenticated retained-storage adapter now returns the held checked plan and joined storage together.',
        'fixed_reproduction': 'storage-review-final-held-plan-selection-result.json',
        'fixed_synthetic_result': 'The held authenticated plan selects the allocator; the second plan reader is never called.',
        'probe_limit': 'Pure mocked adapter/reader routing probe; no selected finalizer or actual control was executed.'}],
    'disproved_suspicion': 'Duplicate external paths with distinct inodes already fail in the initial totals validator; both independent root/file probes confirm refusal.',
    'required_production_code_fixes_pending': [],
    'production_gate_review': {
        'copied_old_b_spender_not_replaced_by_c': True,
        'exact_public_107_file_raw_pin_map_checked': True,
        'c_observed_before_and_after_full_historical_traversal': True,
        'pending_driver_writer_termination_and_outer_launcher_joined_gates_present': True,
        'sampled_supervisor_global_case_quotas_and_cached_external_metadata_checks_present': True,
        'latest_named_file_growth_and_metadata_retained_by_sample': True,
        'low_level_inventory_labels_are_not_execution_authority': True},
    'limitations': ['Machine review, not a human review or scientific evidence.',
        'Synthetic probes and source inspection do not qualify complete protected-control execution.',
        'Kernel or privileged rollback, mutation after a finite final check, complete runtime/native/HTTP host closure remain unqualified.',
        'Complete freeze, immutable public readback, separate execution preread and marker-only c transition retain their independent gates.'],
    'historical_b_mutated': False, 'real_c_journal_created': False,
    'real_c_marker_created': False, 'real_control_dispatched': False,
    'telescope_reads': 0, 'execution_authorized': False,
    'scientific_execution_authorized': False,
    'runner_pin': pin(stable_read(Path(__file__))),
}
destination = BASE/'storage-review-final-review.json'
exclusive(destination, (json.dumps(report, sort_keys=True, indent=2)+'\n').encode())
print(json.dumps({'status': report['status'], 'checks_passed': count,
                  'review': destination.name, 'raw_pin': pin(destination.read_bytes())}, sort_keys=True))
