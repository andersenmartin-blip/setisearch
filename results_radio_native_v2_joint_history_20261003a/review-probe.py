#!/usr/bin/env python3
"""Independent machine static/pin review. No repository source is imported.

This checks selected source contracts and evidence byte identity. It does not
launch a control, read a marker, create or consume a journal, or read telescope
payloads. It does not prove lifetime custody or substitute for human review.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'scripts/radio_native_v2_'
ROLES = {
    'historical_b_scope': 'historical_scope',
    'historical_b_ledger': 'historical_ledger',
    'historical_c_scope': 'historical_scope',
    'historical_c_ledger': 'historical_ledger',
    'prospective_ledger': 'prospective_ledger',
}
D = 'radio-native-v2-control-activation-transition-20261003d'
MARKER = 'config/radio_native_v2_control_activation_20261003d.activate.json'
JOURNAL = '.radio-native-v2-invocation-ledger-20261003d'
SPENT_C = (
    'radio-native-v2-control-activation-transition-20261002c',
    'config/radio_native_v2_control_activation_20261002c.activate.json',
    'f514d782a0f807223e4bc47cb0b330b4b46a198f',
)


def pin(path):
    raw = Path(path).read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def literals(relative):
    tree = ast.parse((ROOT / relative).read_bytes(), filename=relative)
    result = {}
    def value_of(node):
        try:
            return ast.literal_eval(node)
        except (ValueError, TypeError):
            if isinstance(node, ast.Name) and node.id in result:
                return result[node.id]
            if isinstance(node, (ast.Tuple, ast.List)):
                items = []
                for item in node.elts:
                    if isinstance(item, ast.Starred): items.extend(value_of(item.value))
                    else: items.append(value_of(item))
                return tuple(items) if isinstance(node, ast.Tuple) else items
            if isinstance(node, ast.Dict):
                items = {}
                for key, value in zip(node.keys, node.values):
                    if key is None: items.update(value_of(value))
                    else: items[value_of(key)] = value_of(value)
                return items
            if isinstance(node, ast.BinOp):
                left = value_of(node.left); right = value_of(node.right)
                if isinstance(node.op, ast.Add): return left + right
                if isinstance(node.op, ast.Mult): return left * right
                if isinstance(node.op, ast.Sub): return left - right
                if isinstance(node.op, ast.Pow): return left ** right
            raise ValueError('Unsupported static literal expression')
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            try:
                value = value_of(statement.value)
            except (ValueError, TypeError):
                continue
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    result[target.id] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--runtime', type=Path)
    args = parser.parse_args()
    names = ('historical_storage', 'historical_observation', 'control_activation',
        'prospective_spending', 'worker_admission',
        'compact_eight_case_resource_fixture', 'compact_preparation_audit',
        'process_tree_supervisor', 'resource_finalization', 'compact_control_launch')
    sources = {name: PREFIX + name + '.py' for name in names}
    reviewed_helpers = ('results_radio_native_v2_joint_history_20261003a/verify_checkpoint.py',
        'results_radio_native_v2_joint_history_20261003a/capture_preparation.py',
        str(Path(__file__).relative_to(ROOT)))
    reviewed_paths = (*sources.values(), *reviewed_helpers)
    before = {path: pin(ROOT / path) for path in reviewed_paths}
    values = {name: literals(path) for name, path in sources.items()}
    checks = []
    edges = []

    def check(name, condition):
        if not condition:
            raise ValueError('Independent review refused: ' + name)
        checks.append(name)

    for name in ('process_tree_supervisor', 'resource_finalization', 'compact_control_launch'):
        for path, expected in values[name]['BOOTSTRAP_SOURCE_PINS'].items():
            check(name + ' pinned bootstrap ' + path, pin(ROOT / path) == expected)
            edges.append({'owner': sources[name], 'target': path, 'pin': expected})
    independent = (
        ('worker_admission', 'CUSTODY_IMPLEMENTATION_PIN', 'runtime_custody'),
        ('worker_admission', 'SPENDING_IMPLEMENTATION_PIN', 'prospective_spending'),
        ('compact_eight_case_resource_fixture', 'WORKER_ADMISSION_IMPLEMENTATION_PIN', 'worker_admission'),
        ('compact_eight_case_resource_fixture', 'CONTROL_ACTIVATION_IMPLEMENTATION_PIN', 'control_activation'),
        ('compact_eight_case_resource_fixture', 'INVOCATION_SPENDING_IMPLEMENTATION_PIN', 'prospective_spending'),
        ('compact_eight_case_resource_fixture', 'HISTORICAL_OBSERVATION_IMPLEMENTATION_PIN', 'historical_observation'),
        ('compact_eight_case_resource_fixture', 'ACTIVATION_ENVIRONMENT_IMPLEMENTATION_PIN', 'activation_environment'),
        ('historical_observation', 'STORAGE_IMPLEMENTATION_PIN', 'historical_storage'),
    )
    for owner, field, target in independent:
        path = PREFIX + target + '.py'
        expected = values[owner][field]
        check(owner + ' independently pinned ' + target, pin(ROOT / path) == expected)
        edges.append({'owner': sources[owner], 'target': path, 'pin': expected})
    for name in ('historical_storage', 'historical_observation', 'worker_admission'):
        check(name + ' literal complete five component role requirement',
            values[name]['JOINT_HISTORY_COMPONENT_ROLES'] == ROLES)
    check('finalizer literal complete five component role requirement',
        values['resource_finalization']['EXTERNAL_STORAGE_OBSERVATION_ROLES'] == ROLES)
    check('finalizer exact five component ordering',
        values['resource_finalization']['EXTERNAL_STORAGE_ROLES'] == tuple(ROLES))
    check('joined schema equality',
        values['historical_storage']['JOIN_COMPONENT_SCHEMA'] ==
        values['resource_finalization']['EXTERNAL_STORAGE_SCHEMA'])
    for name in ('control_activation', 'prospective_spending'):
        check(name + ' exact distinct d identity and marker',
            values[name]['NAMESPACE'] == D and values[name]['MARKER'] == MARKER)
        check(name + ' c remains permanently spent', SPENT_C in values[name]['SPENT_ACTIVATIONS'])
    check('activation exact d journal',
        values['control_activation']['INVOCATION_LEDGER_DIRECTORY'] == JOURNAL)
    check('spending exact d journal', values['prospective_spending']['LEDGER_DIRECTORY'] == JOURNAL)
    check('worker exact d identity and marker',
        values['worker_admission']['ACTIVATION_NAMESPACE'] == D and
        values['worker_admission']['ACTIVATION_MARKER'] == MARKER)
    check('worker c remains permanently spent', SPENT_C in values['worker_admission']['SPENT_ACTIVATIONS'])
    check('d marker and real journal remain absent', not (ROOT / MARKER).exists() and
        not (ROOT / JOURNAL).exists())
    history = values['historical_observation']['HISTORICAL_INPUT_PINS']
    for path, expected in history.items():
        check('mandatory historical input byte pin ' + path, pin(ROOT / path) == expected)
    check('fixture material covers complete pinned history',
        set(history).issubset(values['compact_eight_case_resource_fixture']['CODE_FILES']))
    immutable_originals = {
        'results_radio_native_v2_compact_control_20261002b/frozen-code/scripts/radio_native_v2_invocation_spending.py':
            {'bytes': 20163, 'sha256': 'd6bba881e0001e61e332eb28b9b6377bcbd9e283641661a89e5360217319ce33'},
        'results_radio_native_v2_compact_control_20261002c/frozen-code/scripts/radio_native_v2_prospective_spending.py':
            {'bytes': 22296, 'sha256': '189da9f870628573e85ae6943a63d79b1390fce0aee8a04e003318cc506e895f'},
        'results_radio_native_v2_compact_control_20261002b/invocation-spending.json':
            {'bytes': 1018, 'sha256': 'f7beaea6e4855f1439c3ae1ecceadf3a4335607fc6940b7b0d0ec1d0c8150f89'},
        'results_radio_native_v2_compact_control_20261002c/invocation-spending.json':
            {'bytes': 1028, 'sha256': '647b91d67c73065399481ba1759e70775b65fc166551391699e617230b75af80'},
        'results_radio_native_v2_control_activation_20261002c/independent-terminal-ledger-review.json':
            {'bytes': 9666, 'sha256': 'b430b7ec8830c733e15e5839a3b281b184281f909615fbbe33b26945a89390c7'},
    }
    for path, expected in immutable_originals.items():
        check('immutable original spender/witness evidence untouched ' + path,
            history[path] == expected and pin(ROOT / path) == expected)
    fixture_ast = ast.parse((ROOT / sources['compact_eight_case_resource_fixture']).read_bytes())
    control = next(node for node in fixture_ast.body if isinstance(node, ast.FunctionDef)
        and node.name == 'run_control')
    calls = {}
    for node in ast.walk(control):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Subscript):
            if isinstance(node.func.slice, ast.Constant):
                calls.setdefault(node.func.slice.value, []).append(node.lineno)
    check('strict original historical observation precedes any new spend',
        max(calls['observe_historical_storage']) < min(calls['consume_once']))
    history_ast = ast.parse((ROOT / sources['historical_observation']).read_bytes())
    for name in ('observe_historical_storage', '_observe_c'):
        function = next(node for node in history_ast.body if isinstance(node, ast.FunctionDef) and node.name == name)
        check(name + ' has no exception handler replacing strict historical refusal',
            not any(isinstance(node, ast.ExceptHandler) for node in ast.walk(function)))
    restoration_path = ROOT / 'results_radio_native_v2_joint_history_20261003a/observation-restored-result.json'
    restoration = json.loads(restoration_path.read_text())
    check('real original b/c spend identity continuity is explicitly refused',
        restoration['original_spend_identities_authenticated'] is False and
        restoration['historical_production_gate_satisfied'] is False and
        set(restoration['original_spend_observer_failures']) == {'b', 'c'} and
        all(value['error'] == 'Invocation ledger directory identity changed'
            for value in restoration['original_spend_observer_failures'].values()))
    check('restored archival inventory preserves unchanged original manifests',
        restoration['original_manifests_replaced'] is False and
        restoration['complete_before_after_inventories_equal'] is True and
        restoration['both_canonical_original_journal_payloads_verified'] is True)
    check('restored archival inventory has exact four disjoint components',
        [component['role'] for component in restoration['components']] == list(ROLES)[:-1] and
        restoration['entry_count'] == 220 and restoration['cross_component_inode_aliases'] == 0)
    refusal_path = ROOT / 'results_radio_native_v2_joint_history_20261003a/production-live-original-identity-refusal.json'
    refusal = json.loads(refusal_path.read_text())
    check('actual current production b/c observers refuse unchanged original witnesses',
        refusal['status'] == 'EXPECTED_BLOCKED_IDENTITY_REFUSALS_VERIFIED' and
        refusal['historical_input_count'] == len(history) == 19 and
        refusal['selected_observer_raw_pin'] == before[sources['historical_observation']] and
        refusal['shared_storage_source_raw_pin'] == before[sources['historical_storage']] and
        refusal['original_witnesses_unchanged'] is True and
        refusal['historical_ledger_rebinding_authorized'] is False and
        refusal['original_identity_continuity_qualified'] is False and
        set(refusal['failures']) == {'b', 'c'} and
        all(value['error'] == 'Invocation ledger directory identity changed'
            for value in refusal['failures'].values()))
    check('actual current production refusal creates no prospective control or spend',
        refusal['new_spends'] == 0 and refusal['protected_control_invocations'] == 0 and
        refusal['future_d_marker_ledger_scope_created'] is False and
        refusal['read_only_audit_denied_events'] == [])
    adapter_raw = (ROOT / reviewed_helpers[1]).read_text()
    check('reviewed metadata adapter includes every selected tested source as input',
        "inputs.update(summary['source_and_test_pins'])" in adapter_raw and
        "if observed != expected['sha256']:" in adapter_raw)
    check('reviewed metadata adapter refuses active stdout/stderr input inodes',
        'Active output log cannot be a frozen input:' in adapter_raw and
        'active = {(os.fstat(fd).st_dev, os.fstat(fd).st_ino) for fd in (1,2)}' in adapter_raw)
    check('reviewed metadata adapter repeats independent audit after persistence',
        'final_audit = audit.audit(persisted_plan, persisted_freeze, repo=REPO)' in adapter_raw and
        'if final_audit != first_audit:' in adapter_raw)
    check('original whole storage cap',
        values['historical_storage']['MAX_STORAGE_BYTES'] == 1536 * 1024**2)
    limits = values['resource_finalization']['LIMITS']
    check('original case and whole storage caps', limits['case_storage_bytes'] == 192 * 1024**2 and
        limits['run_storage_bytes'] == 1536 * 1024**2)
    check('original runtime call/request/response/time/RSS caps', limits == {
        'case_calls': 64, 'run_calls': 512,
        'case_request_bytes': 48 * 1024**2, 'run_request_bytes': 384 * 1024**2,
        'case_response_bytes': 64 * 1024**2, 'run_response_bytes': 512 * 1024**2,
        'case_seconds': 600, 'run_seconds': 4800, 'rss_bytes': 512 * 1024**2,
        'case_storage_bytes': 192 * 1024**2, 'run_storage_bytes': 1536 * 1024**2})
    suite_record = None
    if args.suite:
        suite = json.loads(args.suite.read_text())
        check('selected suite completed successfully', suite['status'] == 'PASSED' and
            suite['failures'] == 0 and suite['errors'] == 0 and suite['skipped'] == 0)
        check('selected suite source snapshot unchanged', suite['source_snapshot_unchanged'] is True and
            suite['initial_source_and_test_pins'] == suite['source_and_test_pins'])
        for path, expected in suite['source_and_test_pins'].items():
            check('selected suite current byte pin ' + path, pin(ROOT / path) == expected)
        suite_record = {'path': str(args.suite), **pin(args.suite),
            'tests': suite['test_count'], 'modules': len(suite['test_modules']),
            'source_test_helper_pin_count': len(suite['source_and_test_pins'])}
    preparation = None
    if args.plan or args.runtime:
        check('both plan and runtime supplied', bool(args.plan and args.runtime))
        plan = json.loads(args.plan.read_text())
        freeze = json.loads(args.runtime.read_text())
        check('plan exact d journal and root', plan['invocation_ledger_root'] ==
            str(ROOT / JOURNAL) and plan['invocation_repository_root'] == str(ROOT))
        check('plan literal complete five role requirement', plan['retained_storage_component_roles'] == ROLES)
        check('plan exact independently pinned history', plan['historical_storage_inputs'] == history)
        check('plan explicitly refuses original historical identity continuity',
            plan['historical_storage_original_identity_continuity_qualified'] is False)
        for path in reviewed_helpers:
            check('reviewed helper bytes included in frozen inputs ' + path,
                freeze['input_sha256s'].get(path) == before[path]['sha256'])
        for path, expected in plan['code_files'].items():
            check('material source/input byte pin ' + path, pin(ROOT / path) == expected)
            hashes = freeze['input_sha256s'] if path.startswith('tests/') or path in history else freeze['code_sha256s']
            check('material mandatory original freeze pin ' + path, hashes.get(path) == expected['sha256'])
        if args.suite:
            for path, expected in suite['source_and_test_pins'].items():
                digest = freeze['code_sha256s'].get(path, freeze['input_sha256s'].get(path))
                check('complete selected tested source covered by current freeze ' + path,
                    digest == expected['sha256'])
        for key in ('execution_authorized', 'scientific_execution_authorized',
                'reservation_authorized', 'rng_authorized', 'native_execution_authorized', 'automatic_retry'):
            if key in plan:
                check('plan no authority ' + key, plan[key] is False)
        preparation = {'plan': {'path': str(args.plan), **pin(args.plan)},
            'runtime': {'path': str(args.runtime), **pin(args.runtime)},
            'material_pin_count': len(plan['code_files']),
            'mandatory_historical_pin_count': len(history),
            'qualification_scope': 'local metadata/source byte review; no actual control or lifetime qualification'}
    after = {path: pin(ROOT / path) for path in reviewed_paths}
    check('reviewed current source byte pins stable during review', before == after)
    print(json.dumps({'schema': 'radio-native-v2-independent-joint-history-machine-review-v1',
        'status': 'PASS', 'reviewer': 'independent machine agent; prior read-only consumer review disclosed',
        'review_scope': 'static source contracts and exact local byte pins; no human or lifetime custody review',
        'checks': checks, 'check_count': len(checks), 'independently_checked_source_edges': edges,
        'reviewed_source_pins': before, 'suite': suite_record, 'preparation': preparation,
        'archival_observation': {'path': str(restoration_path), **pin(restoration_path),
            'original_identity_continuity_qualified': False,
            'actual_historical_production_gate_satisfied': False},
        'actual_production_refusal': {'path': str(refusal_path), **pin(refusal_path),
            'original_identity_continuity_qualified': False, 'new_spends': 0},
        'control_invocations': 0, 'new_marker_created': False, 'real_journal_created_or_consumed': False,
        'telescope_reads': 0, 'rng_draws': 0, 'execution_authorized': False,
        'scientific_execution_authorized': False}, sort_keys=True, separators=(',', ':')))


if __name__ == '__main__':
    main()
