#!/usr/bin/env python3
"""Pure root/map/source-bootstrap contracts with tiny generated source fixtures."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


source = Path(sys.argv[1]).resolve(); raw = source.read_bytes()
assert raw == source.read_bytes()
module = types.ModuleType('held_root_contract_review'); module.__file__ = str(source)
exec(compile(raw, str(source), 'exec'), module.__dict__)
root = module.ORIGINAL_REPOSITORY_ROOT
scope = root+'/generated-review-control'
base_plan = {'invocation_repository_root': root,
             'invocation_ledger_root': root+'/.radio-native-v2-invocation-ledger-20261002c',
             'historical_storage_inputs': copy.deepcopy(module.HISTORICAL_INPUT_PINS),
             'code_files': {**copy.deepcopy(module.HISTORICAL_INPUT_PINS),
                            module.STORAGE_SOURCE: copy.deepcopy(module.STORAGE_IMPLEMENTATION_PIN)}}
base_freeze = {'input_sha256s': {name: value['sha256']
               for name, value in module.HISTORICAL_INPUT_PINS.items()}}
results = []
for action in ('baseline', 'substitute_repository_root', 'historical_b_ledger',
               'scope_outside_root', 'missing_historical_input',
               'extra_historical_input', 'material_history_pin_drift',
               'freeze_history_pin_drift', 'shared_storage_source_substitution',
               'root_dotdot_path'):
    plan = copy.deepcopy(base_plan); freeze = copy.deepcopy(base_freeze)
    selected_root = root; selected_scope = scope
    item = next(iter(module.HISTORICAL_INPUT_PINS))
    if action == 'substitute_repository_root':
        selected_root = '/synthetic/substituted-repository'
        plan.update(invocation_repository_root=selected_root,
            invocation_ledger_root=selected_root+'/.radio-native-v2-invocation-ledger-20261002c')
        selected_scope = selected_root+'/control'
    elif action == 'historical_b_ledger':
        plan['invocation_ledger_root'] = root+'/.radio-native-v2-invocation-ledger'
    elif action == 'scope_outside_root': selected_scope = '/synthetic/control'
    elif action == 'missing_historical_input': plan['historical_storage_inputs'].pop(item)
    elif action == 'extra_historical_input': plan['historical_storage_inputs']['other.json'] = pin(b'x')
    elif action == 'material_history_pin_drift': plan['code_files'][item]['sha256'] = '0'*64
    elif action == 'freeze_history_pin_drift': freeze['input_sha256s'][item] = '0'*64
    elif action == 'shared_storage_source_substitution': plan['code_files'][module.STORAGE_SOURCE]['sha256'] = '0'*64
    elif action == 'root_dotdot_path': selected_root = root+'/../setisearch-repo-20261002'
    try:
        returned = module.validate_contract(plan, freeze,
            repository_root=selected_root, execution_scope=selected_scope)
    except Exception as error:
        outcome = {'name': action, 'accepted': False,
                   'error': type(error).__name__+': '+str(error)}
    else: outcome = {'name': action, 'accepted': True, 'returned_root': returned}
    outcome['expectation_met'] = outcome['accepted'] is (action == 'baseline')
    results.append(outcome)

with tempfile.TemporaryDirectory(prefix='seti-held-source-review-') as temporary:
    code_root = Path(temporary); relative = 'tiny-reviewed-source.py'
    good = b'probe_value = 123\n'; bad = b'probe_value = 999\n'
    for action, candidate in (('held_source_exact_pin', good),
                              ('held_source_same_size_substitution', bad)):
        (code_root/relative).write_bytes(candidate)
        try:
            held = module._module(str(code_root), relative, pin(good))
        except Exception as error:
            outcome = {'name': action, 'accepted': False,
                       'error': type(error).__name__+': '+str(error)}
        else: outcome = {'name': action, 'accepted': True, 'probe_value': held.probe_value}
        outcome['expectation_met'] = outcome['accepted'] is (candidate == good)
        results.append(outcome)
print(json.dumps({'schema': 'radio-native-v2-independent-root-contract-review-v1',
                  'reviewer_kind': 'independent_machine_agent', 'human_review': False,
                  'source_path': str(source), 'source_pin': pin(raw),
                  'runner_pin': pin(Path(__file__).read_bytes()),
                  'synthetic_only': True, 'historical_b_files_read_or_mutated': False,
                  'real_c_journal_created': False, 'real_control_dispatched': False,
                  'telescope_reads': 0, 'cases': results,
                  'all_expectations_met': all(item['expectation_met'] for item in results)},
                 sort_keys=True, indent=2))
