#!/usr/bin/env python3
"""Verify the retained one-control failure and its source-level cause."""
import ast
import hashlib
import json
from pathlib import Path
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path(__file__).resolve().parent
MARKER = ROOT / 'config/radio_native_v2_control_activation_20261002a.activate.json'
FREEZE = ROOT / 'config/radio_native_v2_activation_environment_20261002d.runtime.json'
GIT = Path('/usr/local/bin/git')


def load(path):
    raw = path.read_bytes()
    value = json.loads(raw)
    assert json.dumps(value, sort_keys=True, separators=(',', ':')).encode() + b'\n' == raw
    return value


def function(tree, name):
    return next(node for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)


def main():
    disposition = load(EVIDENCE / 'disposition.json')
    invocation = load(EVIDENCE / 'invocation.json')
    diagnosis = load(EVIDENCE / 'runtime-inventory-diagnosis.json')
    readback = load(EVIDENCE / 'activation-public-readback.json')
    freeze = load(FREEZE)
    assert disposition['status'] == 'CLOSED_FAILED_RUNTIME_CUSTODY_POLICY_MISMATCH'
    assert invocation['invocation_count'] == 1 and invocation['exit_code'] == 1
    assert invocation['scope_created'] is False and invocation['large_inputs_generated'] is False
    assert all(invocation[key] == 0 for key in ('native_case_reservations',
        'native_case_executions', 'scientific_cases_run', 'rng_draws', 'telescope_reads'))
    assert hashlib.sha256(MARKER.read_bytes()).hexdigest() == readback['marker_sha256']
    assert readback['activation_commit'] == disposition['activation_commit']
    assert freeze['runtime_sha256s'][str(GIT)] == diagnosis['expected_sha256']
    before = GIT.stat(follow_symlinks=False)
    assert stat.S_ISREG(before.st_mode) and before.st_nlink > 1
    assert hashlib.sha256(GIT.read_bytes()).hexdigest() == diagnosis['actual_sha256']
    freezer = ast.parse((ROOT / 'scripts/radio_native_v2_runner_freeze.py').read_text())
    fixture = ast.parse((ROOT / 'scripts/radio_native_v2_compact_eight_case_resource_fixture.py').read_text())
    assert not any(isinstance(node, ast.Attribute) and node.attr == 'st_nlink'
                   for node in ast.walk(function(freezer, 'sha_file')))
    assert any(isinstance(node, ast.Attribute) and node.attr == 'st_nlink'
               for node in ast.walk(function(fixture, 'pin')))
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if head == readback['activation_commit']:
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT,
            text=True).strip() == readback['activation_tree']
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD^'], cwd=ROOT,
            text=True).strip() == readback['activation_parent']
    print(json.dumps({'status': 'VERIFIED', 'runtime_path': str(GIT),
        'nlink': before.st_nlink, 'marker_sha256': readback['marker_sha256']},
        sort_keys=True, separators=(',', ':')))


if __name__ == '__main__':
    main()
