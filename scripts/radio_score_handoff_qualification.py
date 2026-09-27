"""Retain bounded score-handoff failures, snapshots and local crash evidence."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import socket
import sys
import time
import traceback
import unittest
from unittest.mock import patch

import numpy as np
from seti_repeater import detector_direct_radio as detector

ROOT = Path(__file__).resolve().parents[1]
CONFIG = 'config/radio_score_handoff_20260927.json'
OUT = ROOT / 'results_radio_score_handoff_2026-09-27'
SOURCES = ['src/seti_repeater/score_handoff_radio.py', 'scripts/radio_score_handoff_fixture.py',
    'scripts/radio_score_handoff_qualification.py', 'tests/test_radio_score_handoff.py',
    'RADIO_SCORE_HANDOFF_2026-09-27_PROTOCOL.md']


def sha(data): return hashlib.sha256(data).hexdigest()
def write(path, value): path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')


def main():
    start = time.perf_counter()
    cfg = json.loads((ROOT / CONFIG).read_text())
    def verify():
        for path, expected in cfg['input_sha256'].items():
            if sha((ROOT / path).read_bytes()) != expected:
                raise ValueError('immutable input changed: ' + path)
    verify(); OUT.mkdir(exist_ok=True)
    n = 1
    while (OUT / f'qualification_{n:02d}').exists(): n += 1
    if n > cfg['offline_budget']['qualification_attempt_limit']:
        raise ValueError('qualification attempt budget exhausted; preserve failure and stop')
    attempt = OUT / f'qualification_{n:02d}'; attempt.mkdir()
    snapshot = {p: (ROOT / p).read_text() for p in [CONFIG, *SOURCES]}
    (attempt / 'source_snapshot.json.gz').write_bytes(gzip.compress(json.dumps(snapshot, sort_keys=True).encode(), mtime=0))
    sys.path.insert(0, str(ROOT / 'tests'))
    suite = unittest.defaultTestLoader.loadTestsFromName('test_radio_score_handoff')
    if suite.countTestCases() > cfg['offline_budget']['new_test_limit']:
        raise ValueError('test budget exceeded')
    log = io.StringIO()
    tested = None
    with patch.object(socket, 'socket', side_effect=AssertionError('offline only')) as sockets, \
            patch.object(detector, 'execute', side_effect=AssertionError('no detector evaluation')) as execute, \
            patch.object(detector, 'calibrate', side_effect=AssertionError('no calibration')) as calibrate:
        try:
            tested = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        except Exception:
            traceback.print_exc(file=log)
    elapsed = time.perf_counter() - start
    (attempt / 'qualification.log').write_text(log.getvalue())
    from test_radio_score_handoff import ScoreHandoffTests
    write(attempt / 'evidence.json', ScoreHandoffTests.evidence)
    passed = tested is not None and tested.wasSuccessful() and elapsed <= cfg['offline_budget']['qualification_seconds_limit']
    write(attempt / 'test_result.json', {'tests_run': tested.testsRun if tested else 0, 'passed': passed,
        'errors': len(tested.errors) if tested else 1, 'failures': len(tested.failures) if tested else 0,
        'elapsed_seconds': elapsed, 'socket_attempts': sockets.call_count,
        'detector_attempts': execute.call_count, 'calibration_attempts': calibrate.call_count,
        'generated_native_values': 98304})
    write(attempt / 'runtime.json', {'python': platform.python_version(), 'numpy': np.__version__,
        'platform': platform.platform(), 'source_sha256': {p: sha(s.encode()) for p, s in snapshot.items()},
        'socket_creation_disabled': True, 'power_loss_simulated': False})
    verify()
    if not passed:
        print(log.getvalue()); raise RuntimeError('failed qualification retained')
    parent = json.loads((ROOT / 'results_radio_execution_envelope_2026-09-27/execution_envelope.json').read_text())
    result = {'schema': 'radio-score-handoff-result-v1',
        'status': 'LOCAL_SCORE_HANDOFF_AND_CHECKPOINT_QUALIFIED_TELESCOPE_BLOCKED',
        'source_commit': cfg['source_commit'], 'new_tests_passed': tested.testsRun,
        'retained_baseline_probe_errors': 1, 'qualification_attempts': n,
        'passing_directory': str(attempt.relative_to(ROOT)),
        'cumulative_generated_native_values': (n + 1) * 98304,
        'independent_fixture_cadences': 1, 'input_sha256': cfg['input_sha256'],
        'parent_blockers_unchanged': parent['blockers'],
        'parent_execution_envelope_sha256': parent['execution_envelope_sha256'],
        'primary': 'neighbor9', 'telescope_requests': 0, 'new_metadata_requests': 0,
        'telescope_reservations': 0, 'new_physical_templates': 0, 'scientific_trials_added': 0,
        'detector_calls': 0, 'calibration_calls': 0, 'fresh_24_case_panel_executed': False,
        'original_m43af_holdouts_opened': False, 'synthetic_ledger_reset': False,
        'old_numerical_or_acquisition_tests_rerun': False,
        'same_scan_pointing_provenance_obtained': False,
        'published_result_corruption_established': False, 'remote_backend_qualified': False,
        'power_loss_durability_qualified': False, 'source_spectral_access_authorized': False,
        'receipt_sha256': ScoreHandoffTests.evidence['complete_reconciliation']['receipt_sha256']}
    if result['cumulative_generated_native_values'] > cfg['offline_budget']['generated_native_values_limit_total']:
        raise ValueError('cumulative local fixture budget exceeded')
    write(OUT / 'result.json', result)
    print(json.dumps({k: result[k] for k in ('status', 'new_tests_passed', 'qualification_attempts',
        'cumulative_generated_native_values', 'receipt_sha256', 'telescope_requests')}, indent=2))


if __name__ == '__main__': main()
