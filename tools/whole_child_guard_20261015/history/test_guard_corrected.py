"""Small real-process regressions. No astronomy, RNG or production-case imports."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import unittest

from guard import assess, durable_json, policy, run_once, run_sequence

OUTPUT = Path(sys.argv[1]).resolve()
OUTPUT.mkdir()
START = time.monotonic()
START_CPU = time.process_time()
OBSERVATIONS = []


def python(code):
    return [sys.executable, '-c', code]


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.folder = OUTPUT / self.id().split('.')[-1]
        self.limits = policy(3, 4, 128 * 1024**2)

    def record(self, **value):
        OBSERVATIONS.append({'test': self.id().split('.')[-1], **value})

    def run_fixture(self, command, limits=None):
        result = run_once(command, self.folder, limits or self.limits)
        self.record(receipt=result)
        return result

    def test_01_success_is_only_resource_compliance(self):
        result = self.run_fixture(python("print('fixture completed')"))
        self.assertTrue(result['resource_acceptance'])
        self.assertTrue(result['launcher_verified'])
        self.assertFalse(result['scientific_integrity_or_QA_or_admission_established'])
        self.assertEqual(result['status'], 'RESOURCE_COMPLIANT_ONLY')

    def test_02_late_finalization_exit_zero_excess_rejected(self):
        # Reproduce the defect: early worker receipt is good, atexit burns CPU,
        # then exits zero. This deliberately unguarded fixture has its own 2s
        # kernel cap below the enclosing finite engineering suite reservation.
        self.folder.mkdir()
        code = """import atexit,json,resource,time
resource.setrlimit(resource.RLIMIT_CPU,(2,2))
early=time.process_time()
print(json.dumps({'early_CPU_s':early,'status':'COMPLETED_CASE_ONLY'}),flush=True)
def finalize():
    end=time.process_time()+0.65
    while time.process_time()<end: pass
atexit.register(finalize)
"""
        start = time.monotonic()
        with (self.folder / 'stdout.log').open('xb') as out:
            proc = subprocess.Popen(python(code), stdout=out)
            _, status, usage = os.wait4(proc.pid, 0)
            proc.returncode = os.waitstatus_to_exitcode(status)
        early = json.loads((self.folder / 'stdout.log').read_text())
        limits = {'cpu_s': 0.35, 'wall_s': 4,
                  'address_space_bytes': 128 * 1024**2}
        receipt = {'wait4_reaped': True, 'exit_code': proc.returncode,
                   'whole_child_CPU_s': usage.ru_utime + usage.ru_stime,
                   'peak_RSS_bytes': usage.ru_maxrss * 1024,
                   'wall_s': time.monotonic() - start,
                   'watchdog_fired': False, 'launcher_verified': False}
        result = assess(receipt, limits)
        self.record(early_receipt=early, final_wait4=receipt, assessment=result,
                    fixture_only_unguarded_exit_zero_reproducer=True,
                    no_guard_launcher_was_used_in_this_deliberate_legacy_reproducer=True)
        durable_json(self.folder / 'LATE_FINALIZATION.json', OBSERVATIONS[-1])
        self.assertLess(early['early_CPU_s'], limits['cpu_s'])
        self.assertEqual(proc.returncode, 0)
        self.assertGreater(receipt['whole_child_CPU_s'], limits['cpu_s'])
        self.assertFalse(result['resource_acceptance'])
        self.assertIn('EXCEEDED_whole_child_CPU_s', result['errors'])

    def test_03_CPU_burn_is_killed_and_reaped(self):
        result = self.run_fixture(python('while True: pass'), policy(2, 5, 128 * 1024**2))
        self.assertFalse(result['resource_acceptance'])
        self.assertEqual(result['exit_code'], -signal.SIGKILL)
        self.assertTrue(result['wait4_reaped'])
        self.assertTrue(result['launcher_verified'])
        self.assertLessEqual(result['whole_child_CPU_s'], 2)

    def test_04_finalizer_cannot_disable_kernel_limit(self):
        code = """import atexit,signal
signal.signal(signal.SIGXCPU,signal.SIG_IGN)
def finalize():
    while True: pass
atexit.register(finalize)
print('worker would have committed before finalization',flush=True)
"""
        result = self.run_fixture(python(code), policy(2, 5, 128 * 1024**2))
        self.assertFalse(result['resource_acceptance'])
        self.assertEqual(result['exit_code'], -signal.SIGKILL)
        self.assertLessEqual(result['whole_child_CPU_s'], 2)

    def test_05_wall_timeout_stops_before_next_submission(self):
        marker = OUTPUT / 'MUST_NOT_EXIST'
        state = run_sequence([python('import time;time.sleep(5)'),
                              python(f"open({str(marker)!r},'w').write('BAD')")],
                             self.folder, policy(2, 0.25, 128 * 1024**2), 4)
        self.record(sequence=state)
        self.assertEqual(state['status'], 'STOPPED_RETAINED_NO_RETRY')
        self.assertEqual(len(state['jobs']), 1)
        self.assertEqual(state['unsubmitted'], [1])
        self.assertTrue(state['jobs'][0]['watchdog_fired'])
        self.assertTrue(state['jobs'][0]['wait4_reaped'])
        self.assertFalse(marker.exists())
        self.assertFalse((self.folder / '0001').exists())

    def test_06_nonzero_exit_rejected(self):
        result = self.run_fixture(python('raise SystemExit(7)'))
        self.assertEqual(result['exit_code'], 7)
        self.assertIn('CHILD_EXIT_FAILED', result['errors'])

    def test_07_address_space_limit_precedes_exec(self):
        result = self.run_fixture(python('x=bytearray(512*1024**2)'))
        self.assertTrue(result['launcher_verified'])
        self.assertFalse(result['resource_acceptance'])
        self.assertNotEqual(result['exit_code'], 0)
        self.assertIn('MemoryError', (self.folder / 'stderr.log').read_text())

    def test_08_duplicate_attempt_retained_without_retry(self):
        result = self.run_fixture(python("print('once')"))
        before = (self.folder / 'WAIT4_RECEIPT.json').read_bytes()
        with self.assertRaises(FileExistsError):
            run_once(python("print('twice')"), self.folder, self.limits)
        self.assertEqual(before, (self.folder / 'WAIT4_RECEIPT.json').read_bytes())
        self.assertTrue(result['resource_acceptance'])

    def test_09_missing_nonfinite_negative_and_bool_rejected(self):
        good = {'wait4_reaped': True, 'exit_code': 0, 'whole_child_CPU_s': 0.1,
                'wall_s': 0.1, 'peak_RSS_bytes': 1024, 'watchdog_fired': False,
                'launcher_verified': True}
        count = 0
        for field in ('whole_child_CPU_s', 'wall_s', 'peak_RSS_bytes'):
            for value in (None, -1, float('nan'), float('inf'), True, '0.1'):
                self.assertFalse(assess({**good, field: value}, self.limits)['resource_acceptance'])
                count += 1
        for field in ('wait4_reaped', 'exit_code', 'watchdog_fired', 'launcher_verified'):
            changed = dict(good)
            del changed[field]
            self.assertFalse(assess(changed, self.limits)['resource_acceptance'])
            count += 1
        self.record(rejected_bad_receipt_variants=count)

    def test_10_exact_cap_no_tolerance_and_C0147_regression(self):
        good = {'wait4_reaped': True, 'exit_code': 0, 'whole_child_CPU_s': 600.0,
                'wall_s': 614.168230966, 'peak_RSS_bytes': 505585664,
                'watchdog_fired': False, 'launcher_verified': True}
        limits = policy(600, 1800, 1024**3)
        self.assertTrue(assess(good, limits)['resource_acceptance'])
        for actual in (600.0000000000001, 601.1514470000001):
            self.assertFalse(assess({**good, 'whole_child_CPU_s': actual}, limits)['resource_acceptance'])
        self.record(historical_CPU_value_rejected_without_rereading_payload=True,
                    exact_cap_accepted_but_next_binary64_value_rejected=True)

    def test_11_parent_interruption_kills_and_reaps(self):
        def interrupt(signum, frame):
            raise RuntimeError('fixture parent interruption')
        previous = signal.signal(signal.SIGALRM, interrupt)
        signal.setitimer(signal.ITIMER_REAL, 0.2)
        try:
            result = self.run_fixture(python('import time;time.sleep(5)'))
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)
        self.assertFalse(result['resource_acceptance'])
        self.assertIn('PARENT_INTERRUPTION', result['errors'])
        self.assertTrue(result['wait4_reaped'])

    def test_12_reservation_denied_before_any_process(self):
        state = run_sequence([python("print('must not run')")], self.folder,
                             self.limits, 2.9)
        self.record(sequence=state)
        self.assertEqual(state['status'], 'STOPPED_RESERVATION_CAPACITY')
        self.assertEqual(state['jobs'], [])
        self.assertEqual(state['unsubmitted'], [0])
        self.assertFalse((self.folder / '0000').exists())


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GuardTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    summary = {'status': 'PASS_ENGINEERING_ONLY' if result.wasSuccessful() else 'FAIL',
               'tests_run': result.testsRun, 'failures': len(result.failures),
               'errors': len(result.errors), 'observations': OBSERVATIONS,
               'suite_self_CPU_s': time.process_time() - START_CPU,
               'suite_reaped_children_CPU_s': child.ru_utime + child.ru_stime,
               'suite_wall_s': time.monotonic() - START,
               'source_pins': {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                               for name in ('guard.py', 'test_guard.py', 'ENGINEERING_SCOPE.json')},
               'scientific_result': False, 'new_telescope_bytes': 0,
               'old_bank_resumed': False, 'new_scientific_bank_created': False}
    durable_json(OUTPUT / 'TEST_RESULT.json', summary)
    raise SystemExit(0 if result.wasSuccessful() else 1)
