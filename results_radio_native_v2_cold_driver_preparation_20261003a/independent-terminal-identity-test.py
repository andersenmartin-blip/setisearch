"""Deterministic terminal identity race with tiny real children and wait4.

Only the first parent identity-presence result and parent selector scheduling
are controlled. The child writes its own actual identity and exits; waitid
WNOWAIT observes that exit without reaping it. Production observe_process
drains both real EOF pipes and owns the sole real wait4 reap.
"""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

import radio_native_v2_compact_eight_case_resource_fixture as fixture


PYTHON = str(Path(sys.executable).resolve())
CHILD_SOURCE = '''import json,os,sys
path,kind=sys.argv[1:]
if kind != 'missing':
    with open(path,'x') as stream:
        if kind == 'malformed': stream.write('{')
        else:
            value={'procfs_pid':int(os.readlink('/proc/self')),'namespace_pid':os.getpid()}
            if kind == 'forged': value['procfs_pid'] += 1
            json.dump(value,stream)
        stream.flush(); os.fsync(stream.fileno())
'''


class ObserverTerminalIdentityTests(unittest.TestCase):
    def exercise_terminal_boundary(self, kind):
        with tempfile.TemporaryDirectory(prefix='seti-terminal-identity-test-') as directory:
            root = Path(directory); identity_path = root / 'identity.json'
            real_exists = Path.exists
            real_mapping = fixture.launched_child_identity
            real_selector = fixture.selectors.DefaultSelector
            real_wait4 = os.wait4
            state = {'presence_checks': 0, 'select_calls': 0, 'reaps': []}

            def exists(path):
                if path == identity_path:
                    state['presence_checks'] += 1
                    if state['presence_checks'] == 1:
                        return False
                return real_exists(path)

            def map_child(pid):
                state['namespace_pid'] = pid
                state['bound_identity'] = real_mapping(pid)
                return state['bound_identity']

            def select_factory():
                selector = real_selector(); real_select = selector.select

                def select_after_exit(timeout=None):
                    state['select_calls'] += 1
                    stop = time.monotonic() + 2
                    terminal = None
                    while terminal is None and time.monotonic() < stop:
                        terminal = os.waitid(os.P_PID, state['namespace_pid'],
                            os.WEXITED | os.WNOWAIT | os.WNOHANG)
                        if terminal is None: time.sleep(0.001)
                    self.assertIsNotNone(terminal, 'Tiny child must exit before EOF scheduling')
                    self.assertEqual(terminal.si_pid, state['namespace_pid'])
                    self.assertEqual(terminal.si_code, os.CLD_EXITED)
                    self.assertEqual(terminal.si_status, 0)
                    state['identity_exists_at_terminal'] = real_exists(identity_path)
                    events = real_select(0.05)
                    self.assertEqual({key.data for key, _ in events}, {'stdout', 'stderr'})
                    return events

                selector.select = select_after_exit
                return selector

            def wait4(pid, flags):
                result = real_wait4(pid, flags)
                if result[0]:
                    state['reaps'].append({'pid': result[0], 'status': result[1],
                        'peak_rss_bytes': result[2].ru_maxrss * 1024})
                return result

            error = None
            with mock.patch.object(Path, 'exists', exists), \
                    mock.patch.object(fixture, 'launched_child_identity', map_child), \
                    mock.patch.object(fixture.selectors, 'DefaultSelector', select_factory), \
                    mock.patch.object(fixture.os, 'wait4', wait4):
                try:
                    fixture.observe_process([PYTHON, '-I', '-S', '-B', '-c', CHILD_SOURCE,
                        str(identity_path), kind], root, 'terminal', identity_path,
                        deadline=time.monotonic() + 3, pipe_output=True)
                except RuntimeError as failure:
                    error = failure

            observed = fixture.small_json(root / 'terminal-observation.json')
            self.assertEqual(state['select_calls'], 1)
            self.assertEqual(len(state['reaps']), 1)
            self.assertEqual(state['reaps'][0]['pid'], state['namespace_pid'])
            self.assertEqual(os.waitstatus_to_exitcode(state['reaps'][0]['status']), 0)
            self.assertEqual(observed['exit_code'], 0)
            self.assertTrue(observed['direct_child_reaped'])
            self.assertTrue(observed['includes_entire_child_lifetime'])
            self.assertEqual(observed['wait4_ru_maxrss_bytes'], state['reaps'][0]['peak_rss_bytes'])
            self.assertEqual(observed['bound_child_identity'], state['bound_identity'])
            self.assertFalse(observed['complete_descendant_wait_chain_verified'])
            self.assertEqual((root / 'terminal-stdout.log').read_bytes(), b'')
            self.assertEqual((root / 'terminal-stderr.log').read_bytes(), b'')
            state['observed'] = observed
            state['error'] = None if error is None else str(error)
            self.probe_evidence = state
            return observed, error

    def test_identity_published_before_terminal_eof_is_verified(self):
        observed, error = self.exercise_terminal_boundary('valid')
        if error is not None: raise error
        self.assertTrue(observed['reported_identity_verified'])
        self.assertIsNone(observed['reason'])
        self.assertTrue(observed['complete_pipe_output'])

    def test_forged_terminal_identity_is_still_refused(self):
        observed, error = self.exercise_terminal_boundary('forged')
        self.assertIsInstance(error, RuntimeError)
        self.assertFalse(observed['reported_identity_verified'])
        self.assertIsNotNone(observed['reason'])

    def test_missing_terminal_identity_is_still_refused(self):
        observed, error = self.exercise_terminal_boundary('missing')
        self.assertIsInstance(error, RuntimeError)
        self.assertFalse(observed['reported_identity_verified'])
        self.assertIsNotNone(observed['reason'])

    def test_malformed_terminal_identity_is_still_refused(self):
        observed, error = self.exercise_terminal_boundary('malformed')
        self.assertIsInstance(error, RuntimeError)
        self.assertFalse(observed['reported_identity_verified'])
        self.assertIsNotNone(observed['reason'])


if __name__ == '__main__':
    unittest.main()
