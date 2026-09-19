#!/usr/bin/env python3
"""Repeat frozen LS7P offline and compare the retained reconstruction bytes.

The producer and independent scalar auditor are unchanged. Only their OUT
directory is rebound, leaving their source ROOT and scientific inputs intact.
Use the exact f42aa21 source checkout, including the published prerequisite
data, and place the released results_ls7p_inputs/response under that checkout.
No acquisition function is called. The original output folders are read only.
"""
import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest

FREEZE = 'f42aa216b25779d55cd1fabd25545d3277abcfa5'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--verification-root', required=True, type=Path)
    parser.add_argument('--source-inventory', required=True, type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    out = args.verification_root.resolve()
    assert not out.exists(), 'Refuse completed verification overwrite'
    started = datetime.now(timezone.utc).isoformat()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    assert head == FREEZE, (head, FREEZE)
    inventory = json.loads(args.source_inventory.read_text())
    assert inventory['source_commit'] == FREEZE
    for row in inventory['files']:
        p = root / row['path']
        assert p.is_file() and p.stat().st_size == row['bytes'], row['path']
        assert sha(p) == row['sha256'], row['path']
    retained = root / 'results_ls7p_response'
    before = {p.name: sha(p) for p in sorted(retained.iterdir()) if p.is_file()}
    input_before = {str(p.relative_to(root)): sha(p)
                    for p in sorted((root / 'results_ls7p_inputs').rglob('*')) if p.is_file()}
    out.mkdir(parents=True)
    sys.path.insert(0, str(root / 'src'))
    sys.path.insert(0, str(root / 'scripts'))
    with (out / 'known_answers.log').open('w') as log:
        suite = unittest.defaultTestLoader.discover(str(root / 'tests'), pattern='test_ls7p_pixel_centroid.py')
        tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        assert tests.wasSuccessful() and tests.testsRun == 7
    fresh = out / 'response'
    producer = importlib.import_module('ls7p_evaluate')
    assert producer.ROOT == root
    producer.OUT = fresh
    with (out / 'evaluation.log').open('w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        producer.main()
    auditor = importlib.import_module('ls7p_audit')
    assert auditor.ROOT == root
    auditor.OUT = fresh
    with (out / 'audit.log').open('w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        auditor.main()
    after = {p.name: sha(p) for p in sorted(fresh.iterdir()) if p.is_file()}
    assert set(before) == set(after)
    differences = [p for p in before if before[p] != after[p]]
    assert not differences, differences
    assert before == {p.name: sha(p) for p in sorted(retained.iterdir()) if p.is_file()}
    assert input_before == {str(p.relative_to(root)): sha(p)
                            for p in sorted((root / 'results_ls7p_inputs').rglob('*')) if p.is_file()}
    versions = {n: importlib.import_module(n).__version__ for n in ['numpy', 'scipy', 'astropy', 'matplotlib']}
    audit = json.loads((fresh / 'audit.json').read_text())
    report = {
        'status': 'PASS', 'operation': 'offline_reproduction_of_retained_2026_09_15_reconstruction',
        'original_earlier_run_recovered': False, 'started_utc': started,
        'finished_utc': datetime.now(timezone.utc).isoformat(),
        'source_commit': head, 'source_files_verified': len(inventory['files']),
        'source_inventory_sha256': sha(args.source_inventory),
        'verification_driver_sha256': sha(Path(__file__)),
        'python': platform.python_version(), 'packages': versions,
        'known_answer_tests_passed': tests.testsRun,
        'result_files_compared': len(before), 'byte_identical_result_files': len(after),
        'result_file_sha256': after, 'retained_input_files_unchanged': len(input_before),
        'retained_outputs_unchanged': True,
        'independent_audit_status': audit['status'],
        'independent_numeric_comparisons': audit['numeric_comparisons'],
        'new_archive_transfers': 0, 'new_observational_inputs': 0,
        'new_target_corrections': 0, 'new_native_prediction_windows': 0,
        'new_pulse_transfer_cases': 0,
        'execution_adjustment': 'Rebind OUT only; frozen producer, auditor and source ROOT unchanged.'
    }
    (out / 'verification.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'result_file_sha256'}, indent=2))


if __name__ == '__main__':
    main()
