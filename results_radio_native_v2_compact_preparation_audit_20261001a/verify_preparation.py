"""Reproduce the read-only preparation inventory/audit; no large worker run."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parents[1]
for folder in (REPO/'src', REPO/'scripts'):
    if str(folder) not in sys.path:
        sys.path.insert(0,str(folder))

import radio_native_v2_compact_eight_case_resource_fixture as fixture
import radio_native_v2_runner_freeze as freezer
import radio_native_v2_compact_preparation_audit as auditor

OUT = REPO/'results_radio_native_v2_compact_preparation_audit_20261001a'
PLAN = 'config/radio_native_v2_compact_eight_input_control_20261001b.plan.json'
FREEZE = 'config/radio_native_v2_compact_preparation_review_20261001a.runtime.json'
INPUTS = [PLAN,
    'tests/test_radio_native_v2_compact_eight_case_resource_fixture.py',
    'tests/test_radio_native_v2_compact_preparation_audit.py',
    'tests/test_radio_native_v2_process_tree_supervisor.py',
    str(Path(__file__).relative_to(REPO))]


def exact_file(relative, value):
    path=REPO/relative; raw=fixture.canonical(value)
    if path.exists():
        if path.read_bytes()!=raw:
            raise RuntimeError('Existing preparation output differs; do not overwrite: '+relative)
    else:
        fixture.write(path,raw)
    return raw


if __name__ == '__main__':
    started=time.monotonic()
    plan=fixture.build_plan(REPO)
    exact_file(PLAN,plan)
    freeze=freezer.capture(REPO,INPUTS)
    exact_file(FREEZE,freeze)
    with tempfile.TemporaryDirectory(prefix='seti-readonly-materialization-') as directory:
        material=Path(directory)
        fixture.copy_code(REPO,material/'code',plan['code_files'])
        derived=material/'derived';derived.mkdir()
        for name,raw in fixture.templates((REPO/fixture.CODE_FILES[0]).read_text()).items():
            fixture.write(derived/name,raw)
        result=auditor.audit(plan,freeze,repo=REPO,
            materialized_code_root=material/'code',derived_root=derived)
    exact_file(str((OUT/'independent-preparation-audit.json').relative_to(REPO)),result)
    summary={'schema':'radio-native-v2-preparation-review-summary-v1',
        'status':result['status'],'review_kind':'READ_ONLY_PREPARATION_INVENTORY_AND_MATERIALIZED_CODE',
        'plan':fixture.pin(REPO/PLAN),'original_local_freeze':fixture.pin(REPO/FREEZE),
        'independent_audit':fixture.pin(OUT/'independent-preparation-audit.json'),
        'repository_code_files':len(freeze['repository_code_inventory']),
        'input_files':len(freeze['input_file_inventory']),
        'original_runtime_files':len(freeze['runtime_file_inventory']),
        'runtime_supplement_files':len(plan['engineering_runtime_supplement']['files']),
        'joined_runtime_files':result['runtime_and_supplement_union_files'],
        'read_only_inventory_and_audit_seconds':time.monotonic()-started,
        'public_immutable_preread_verified':False,'all_execution_blockers_closed':False,
        'eight_input_resource_control_executed':False,'complete_runtime_authority_granted':False,
        **fixture.AUTHORITY}
    fixture.write(OUT/'verification-summary.json',summary)
    print(json.dumps({key:summary[key] for key in ('status','repository_code_files','original_runtime_files',
        'joined_runtime_files','read_only_inventory_and_audit_seconds')},sort_keys=True))
