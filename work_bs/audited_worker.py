"""Python audit-event recorder around the unchanged BS diagnostic CLI.

This is NOT a syscall trace. Python audit hooks do not cover writes, fsync,
native extension activity, other processes, or host workspace reconciliation.
Events identify operations attempted through Python, not their success. Only
the process's own fixture-path operations and descriptor chmod/truncate events
are recorded. No earlier SETI source or artifact is modified.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import time

EVENTS = frozenset(('open', 'os.chmod', 'os.link', 'os.remove', 'os.rename', 'os.truncate'))
MAX_AUDIT_BYTES = 8 * 1024 * 1024


def safe_argument(value):
    if value is None or isinstance(value, (str, int, bool, float)):
        return value
    if isinstance(value, bytes):
        return os.fsdecode(value)
    return repr(value)


def write_all(fd, payload):
    view = memoryview(payload)
    while view:
        try:
            count = os.write(fd, view)
        except InterruptedError:
            continue
        if count <= 0:
            raise OSError('Incomplete Python audit-log write')
        view = view[count:]


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--audit', required=True, type=Path)
    options, rest = parser.parse_known_args()
    if rest[:1] == ['--']:
        rest = rest[1:]
    if rest.count('--output-dir') != 1:
        raise ValueError('Exactly one diagnostic --output-dir is required')
    output_index = rest.index('--output-dir') + 1
    if output_index >= len(rest):
        raise ValueError('Missing diagnostic output directory')
    output = Path(rest[output_index])
    audit = options.audit
    if not audit.is_absolute() or not output.is_absolute():
        raise ValueError('Audit and diagnostic output paths must be absolute')
    if audit.parent != audit.parent.resolve(strict=True) or output.parent != audit.parent:
        raise ValueError('Audit and output must share the canonical capture directory')
    if audit.name in ('', '.', '..') or audit.exists() or audit.is_symlink():
        raise FileExistsError('Audit log must be a new exclusive regular path')
    if output.exists() or output.is_symlink():
        raise FileExistsError('Diagnostic output directory must not exist')
    fixture_root = output / 'payload'
    fd = os.open(audit, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    bytes_written = 0
    event_count = 0
    active = True
    append_lock = threading.RLock()

    def append(value):
        nonlocal bytes_written
        raw = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()
        with append_lock:
            if bytes_written + len(raw) > MAX_AUDIT_BYTES:
                raise RuntimeError('Fixed Python audit-log cap exceeded')
            write_all(fd, raw)
            bytes_written += len(raw)

    def fixture_path(value):
        if not isinstance(value, (str, bytes)):
            return False
        value = os.fsdecode(value)
        path = Path(value)
        if path.is_absolute():
            return path.parent == fixture_root and (path.name.endswith('.jsonl') or path.name.endswith('.jsonl.pending'))
        # The unchanged BR writer addresses these basenames through its
        # separately opened fixture-directory descriptor.
        return path.name == value and value.startswith(('fixture_', '.fixture_')) and (value.endswith('.jsonl') or value.endswith('.jsonl.pending'))

    def audit_hook(event, args):
        nonlocal event_count
        if not active or event not in EVENTS:
            return
        descriptor_change = event in ('os.chmod', 'os.truncate') and args and isinstance(args[0], int)
        if not descriptor_change and not any(fixture_path(value) for value in args):
            return
        record = {'event': event, 'time_ns': time.time_ns(), 'monotonic_ns': time.monotonic_ns(),
                  'pid': os.getpid(), 'args': [safe_argument(value) for value in args]}
        if descriptor_change:
            try:
                record['descriptor_path_at_event'] = os.readlink('/proc/self/fd/' + str(args[0]))
            except OSError as exc:
                record['descriptor_resolution_error'] = type(exc).__name__ + ': ' + str(exc)
        append(record)
        event_count += 1

    exit_code = None
    failure = None
    try:
        append({'event': 'BS_PYTHON_AUDIT_START', 'schema': 'SETI_BS_PYTHON_AUDIT_V1',
                'time_ns': time.time_ns(), 'pid': os.getpid(), 'fixture_root': str(fixture_root),
                'events': sorted(EVENTS), 'syscall_trace': False,
                'limitations': 'Python attempted-operation events only; no write/fsync coverage, successful-return evidence, external-process attribution or host reconciliation visibility.'})
        sys.addaudithook(audit_hook)
        path = Path(__file__).with_name('diagnostic.py')
        spec = importlib.util.spec_from_file_location('bs_audited_diagnostic', path)
        diagnostic = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(diagnostic)
        sys.argv = [str(path), *rest]
        exit_code = diagnostic.main()
        return exit_code
    except BaseException as exc:
        failure = type(exc).__name__ + ': ' + str(exc)
        raise
    finally:
        active = False
        try:
            append({'event': 'BS_PYTHON_AUDIT_END', 'time_ns': time.time_ns(), 'pid': os.getpid(),
                    'diagnostic_return_code': exit_code, 'exception': failure,
                    'recorded_operation_events': event_count, 'bytes_before_footer': bytes_written})
            os.fsync(fd)
        finally:
            os.close(fd)


if __name__ == '__main__':
    sys.exit(main())
