#!/usr/bin/env python3
"""Pure check_storage plan-selection probe. No source dispatch or filesystem IO.

The authenticated historical adapter is mocked to return a held reviewed plan;
the legacy second plan.json reader is mocked to return different unchecked data.
The allocator records which plan the implementation selects. This isolates the
TOCTOU source-selection boundary without executing any selected finalizer.
"""
import hashlib
import json
from pathlib import Path
import sys
import types


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


source = Path(sys.argv[1]).resolve(); raw = source.read_bytes()
assert raw == source.read_bytes()
module = types.ModuleType('held_plan_selection_review'); module.__file__ = str(source)
exec(compile(raw, str(source), 'exec'), module.__dict__)
held_plan = {'review_probe_identity': 'authenticated-held-plan'}
unchecked_plan = {'review_probe_identity': 'unchecked-second-file-read'}
joined = {'review_probe_identity': 'authenticated-held-join'}
calls = {'authenticated_adapter': 0, 'legacy_join_adapter': 0, 'second_plan_reader': 0}


def authenticated(*args, **kwargs):
    calls['authenticated_adapter'] += 1
    return held_plan, joined


def legacy(*args, **kwargs):
    calls['legacy_join_adapter'] += 1
    return joined


def second_reader(*args, **kwargs):
    calls['second_plan_reader'] += 1
    return unchecked_plan


module._authenticated_retained_storage = authenticated
module.persistent_ledger_storage = legacy
module.small_json = second_reader
module.allocate_workload_storage = lambda scope, plan, value, **options: {
    'selected_plan': plan['review_probe_identity'], 'selected_join': value['review_probe_identity']}
selected = module.check_storage('/synthetic/current-control', repo='/synthetic/material-code')
passed = selected['selected_plan'] == held_plan['review_probe_identity'] and calls['second_plan_reader'] == 0
print(json.dumps({'schema': 'radio-native-v2-independent-held-plan-selection-review-v1',
                  'reviewer_kind': 'independent_machine_agent', 'human_review': False,
                  'source_path': str(source), 'source_pin': pin(raw),
                  'runner_pin': pin(Path(__file__).read_bytes()), 'synthetic_only': True,
                  'result': selected, 'calls': calls, 'all_expectations_met': passed,
                  'selected_finalizer_executed': False, 'real_control_dispatched': False,
                  'real_c_journal_created': False, 'telescope_reads': 0},
                 sort_keys=True, indent=2))
