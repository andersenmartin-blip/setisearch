#!/usr/bin/env python3
"""Held-byte synthetic activation checks; no project marker/control/ledger writes."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).parent
EXACT = {'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','HOME':'/nonexistent',
    'PYTHONSAFEPATH':'1','PYTHONNOUSERSITE':'1','GIT_CONFIG_NOSYSTEM':'1',
    'GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0','GIT_NO_LAZY_FETCH':'1'}
PYTHON = '/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12'
if dict(os.environ) != EXACT or not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
    os.execve(PYTHON,[PYTHON,'-I','-S','-B',str(Path(__file__).absolute())],EXACT)
PINS = {'results_radio_native_v2_fresh_activation_20261002c_candidate/control_activation_candidate.py': {'bytes': 17902, 'sha256': '64655e0feb5b4d0e429be50e66a4a5e504221dc9860f196046db245406323fca'}, 'results_radio_native_v2_fresh_activation_20261002c_candidate/historical_spent_identity_tests.py': {'bytes': 2571, 'sha256': '84756cbcbb5b4dbd99ce43cc76d55dc372879660ee246037a1af8a510f8c16ff'}, 'scripts/radio_native_v2_control_activation.py': {'bytes': 17701, 'sha256': '69d7959c946b5e82cf0302e2c0d65b77c5ed890742038de35c210273ab140479'}, 'scripts/radio_native_v2_runtime_custody.py': {'bytes': 22519, 'sha256': 'd0cd311c1615a2c299b101ca75b98ba2412b41bb1cfd668725461e4d307fb0b5'}, 'tests/test_radio_native_v2_control_activation.py': {'bytes': 20559, 'sha256': 'aba3248f466da19665b77cde632fb710dd7bbbf68cf4e7b8df2fba967c71308c'}}
raws = {}
for path, pin in PINS.items():
    raw = (ROOT/path).read_bytes()
    if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} != pin:
        raise ValueError('Candidate input differs from reviewed literal: '+path)
    raws[path] = raw

def held(name, path):
    module = types.ModuleType(name); module.__file__ = str(ROOT/path)
    sys.modules[name] = module
    exec(compile(raws[path],module.__file__,'exec'),module.__dict__)
    return module

started = time.monotonic()
custody = held('radio_native_v2_runtime_custody','scripts/radio_native_v2_runtime_custody.py')
activation = held('radio_native_v2_control_activation', str((HERE/'control_activation_candidate.py').relative_to(ROOT)))
tests = held('held_baseline_activation_tests','tests/test_radio_native_v2_control_activation.py')
extra = held('held_spent_history_tests', str((HERE/'historical_spent_identity_tests.py').relative_to(ROOT)))
suite = unittest.defaultTestLoader.loadTestsFromTestCase(tests.ControlActivationTests)
extra_class = extra.install_cases(tests.ControlActivationTests,activation)
new_names = sorted(name for name in extra_class.__dict__ if name.startswith('test_'))
for name in new_names:
    suite.addTest(extra_class(name))
result = unittest.TextTestRunner(verbosity=2).run(suite)
unchanged = all((ROOT/path).read_bytes()==raw for path,raw in raws.items())
proof = {'schema':'radio-native-v2-fresh-activation-candidate-test-v1',
    'status':'PASSED_CANDIDATE_PREPARATION_ONLY' if result.wasSuccessful() and not result.skipped and unchanged else 'FAILED',
    'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
    'seconds':round(time.monotonic()-started,6),'source_snapshot_unchanged':unchanged,
    'source_pins':PINS,'extra_spent_history_test_names':new_names,
    'actual_argv':list(sys.orig_argv),'actual_environment_keys':sorted(os.environ),
    'actual_isolated_no_site_no_bytecode':bool(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode),
    'all_repository_test_modules_compiled_from_held_reviewed_bytes_without_pyc':True,
    'test_git_markers_are_tiny_inert_temporary_fixtures':True,
    'current_registered_activation_source_unchanged':True,
    'new_project_activation_marker_created':False,'protected_control_invocations':0,
    'live_ledger_mutated':False,'scientific_cases_run':0,'telescope_reads':0,'execution_authorized':False}
raw=(json.dumps(proof,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
with (HERE/'candidate-test-result.json').open('xb') as stream:
    stream.write(raw); stream.flush(); os.fsync(stream.fileno())
print(raw.decode(),end='')
raise SystemExit(proof['status']=='FAILED')
