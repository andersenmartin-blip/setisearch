#!/usr/bin/env python3
"""Bounded exact-before/fixed-after callback probe; no protected invocation."""
import hashlib
import json
import os
from pathlib import Path
import re
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
SOURCE = 'scripts/radio_native_v2_compact_eight_case_resource_fixture.py'
ORIGINAL_PIN = {'bytes': 128081, 'sha256': 'caca109cbd029f56c05861df183371349dd58f9c6ed0b96aedb8a7960a3feb30'}


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, raw):
    with path.open('xb') as target:
        target.write(raw); target.flush(); os.fsync(target.fileno())


current_raw = (REPO / SOURCE).read_bytes()
old = current_raw.decode().replace(
    'def _authenticated_retained_storage(scope, *, repo=REPO):\n    """Retain the checked plan snapshot alongside its live joined storage."""',
    'def persistent_ledger_storage(scope, *, repo=REPO):\n    """Authenticate exact retained scope evidence before measuring its ledger."""', 1)
old = old.replace(
    "    joined=observe_authenticated_invocation_storage(repo,records['plan'],records['freeze'],\n        records['activation_receipt'],records['invocation_spending'],execution_scope=scope,repository_root=root)\n    return records['plan'],joined\n\n\ndef persistent_ledger_storage(scope, *, repo=REPO):\n    \"\"\"Authenticate exact retained scope evidence before measuring its ledger.\"\"\"\n    return _authenticated_retained_storage(scope,repo=repo)[1]",
    "    return observe_authenticated_invocation_storage(repo,records['plan'],records['freeze'],\n        records['activation_receipt'],records['invocation_spending'],execution_scope=scope,repository_root=root)", 1)
old = old.replace(
    '    plan,joined=_authenticated_retained_storage(scope,repo=repo)\n    return allocate_workload_storage(scope,plan,joined,repo=repo)',
    "    joined=persistent_ledger_storage(scope,repo=repo)\n    plan=small_json(scope/'plan.json')\n    return allocate_workload_storage(scope,plan,joined,repo=repo)", 1)
# Root subsequently refreshed only these source-edge literals. Restore the
# captured original values before authenticating the complete old source.
for name, literal in {
        'WORKER_ADMISSION_IMPLEMENTATION_PIN': "{'bytes': 75309, 'sha256': '475c2884f87f10986e15df57bbb9b5ee7c0652cf37604b2f7f03d9fd277142ae'}",
        'CONTROL_ACTIVATION_IMPLEMENTATION_PIN': "{'bytes':17701,'sha256':'69d7959c946b5e82cf0302e2c0d65b77c5ed890742038de35c210273ab140479'}",
        'INVOCATION_SPENDING_IMPLEMENTATION_PIN': "{'bytes': 22292, 'sha256': '5e449c1f7d5b6ae204783a988116990b588601e7f8d1e35fee1d02faba61b950'}"}.items():
    old, count = re.subn('^' + name + r' = .*$', name + ' = ' + literal, old, count=1, flags=re.M)
    if count != 1: raise ValueError('Exact old bootstrap literal not recovered')
old_raw = old.encode()
if pin(old_raw) != ORIGINAL_PIN:
    raise ValueError('Recovered source differs from exact original retained candidate pin')
write(OUT / 'ledger-review-original-plan-reread-fixture.source.txt', old_raw)


def module(raw, name):
    value = {'__name__': name, '__file__': str(REPO / SOURCE)}
    exec(compile(raw, str(REPO / SOURCE), 'exec'), value)
    return value


old_module = module(old_raw, 'original_plan_reread_probe')
current_module = module(current_raw, 'fixed_plan_snapshot_probe')
checked_plan = {'sentinel': 'authenticated-before-rename'}
replaced_plan = {'sentinel': 'replaced-after-admission'}
joined = {'sentinel': 'live-joined-storage'}
scope = Path('/tmp/inert-plan-reread-callback-scope')
with mock.patch.dict(old_module, {
        'persistent_ledger_storage': lambda *args, **kwargs: joined,
        'small_json': lambda *args, **kwargs: replaced_plan,
        'allocate_workload_storage': lambda scope, plan, external, **kwargs: plan}):
    original_result = old_module['check_storage'](scope)
with mock.patch.dict(current_module, {
        '_authenticated_retained_storage': lambda *args, **kwargs: (checked_plan, joined),
        'small_json': mock.Mock(side_effect=AssertionError('authenticated plan reread')),
        'allocate_workload_storage': lambda scope, plan, external, **kwargs: plan}):
    fixed_result = current_module['check_storage'](scope)
    reread_calls = current_module['small_json'].call_count
result = {'schema': 'seti-fixture-plan-reread-self-review-probe-v1',
    'reviewer': 'machine_agent_author_self_review', 'independent_human_review_claimed': False,
    'original_candidate_pin': ORIGINAL_PIN, 'fixed_candidate_pin': pin(current_raw),
    'original_gap_reproduced_with_exact_source': original_result == replaced_plan,
    'fixed_checked_plan_preserved': fixed_result == checked_plan,
    'fixed_untrusted_plan_reread_calls': reread_calls,
    'probe_kind': 'bounded deterministic callbacks around exact candidate check_storage function',
    'full_activation_or_spend_authentication_invoked': False,
    'protected_invocation_executed': False, 'project_c_journal_accessed': False,
    'invocation_consumed': False, 'activation_marker_written': False, 'control_executed': False,
    'lifetime_accounting_proved': False, 'whole_control_qualified': False}
raw = json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'
write(OUT / 'ledger-review-plan-reread-probe.json', raw)
print(raw.decode(), end='')
if original_result != replaced_plan or fixed_result != checked_plan or reread_calls:
    raise SystemExit(1)
