"""BS deterministic file-lifecycle diagnostics; no SETI arrays or RNG.

Uses the unchanged BQ and BR writer classes on explicitly artificial JSONL.
The caller freezes the exact command and enforces the whole process budget.
Nothing in this module opens A04, powers, score arrays, or previous outputs.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import stat
import struct
import sys
import threading
import time
import traceback

REPO = Path(__file__).resolve().parents[1]
SOURCE_PINS = {
    'bq': ('work_bq/stream_association.py', '455ad449bbe7ddd540b559461620e652c15bffe76b0c597648f8fd780a5fa115'),
    'br': ('work_br/stream_closure.py', '8b3e3887b1b548e06d28cab4fcba127815c047f28b5c6cd72164472c99ced814'),
}
MAX_RECORDS = 45000
MAX_EVENTS = 20000
STAT_KEYS = ('device', 'inode', 'size', 'mode', 'mtime_ns', 'ctime_ns', 'nlink')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def file_info(info):
    return dict(zip(STAT_KEYS, (info.st_dev, info.st_ino, info.st_size,
                               stat.S_IMODE(info.st_mode), info.st_mtime_ns,
                               info.st_ctime_ns, info.st_nlink)))


def fixture_record(stream_index, record_index):
    """The payload is a constant string, not samples from any RNG."""
    return {'schema': 'BS_ARTIFICIAL_FILE_FIXTURE_V1', 'stream': stream_index,
            'index': record_index,
            'status': 'OFF_VETO' if record_index % 3 == 0 else 'THREE_ON_FAIL',
            'payload': '0123456789abcdef' * 118 + '0123456789ab'}


def encode(record):
    return (json.dumps(record, sort_keys=True, separators=(',', ':'),
                       allow_nan=False) + '\n').encode('utf-8')


def load_writer(kind):
    relative, expected = SOURCE_PINS[kind]
    path = REPO / relative
    actual = sha(path)
    if actual != expected:
        raise ValueError('Frozen writer source mismatch: ' + relative)
    spec = importlib.util.spec_from_file_location('bs_frozen_' + kind, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, {'path': relative, 'sha256': actual, 'bytes': path.stat().st_size}


class LifecycleMonitor:
    """Observe pathname and held-descriptor identities without changing bytes.

    The fixed 20 ms sampling interval cannot observe every transient change.
    inotify is independent corroboration, not PID attribution; syscall tracing
    is the caller's separate responsibility. Descriptor handles remain open
    through final sampling, so replacement can be distinguished from mutation.
    """
    def __init__(self, payload):
        self.payload = Path(payload)
        self.start = time.monotonic()
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.samples, self.events, self.violations, self.errors = [], [], [], []
        self.last, self.held, self.closed = {}, {}, {}
        self.dropped = 0
        self.inotify_fd = None
        self.inotify_error = None
        try:
            libc = ctypes.CDLL(None, use_errno=True)
            init = libc.inotify_init1
            init.argtypes, init.restype = [ctypes.c_int], ctypes.c_int
            add = libc.inotify_add_watch
            add.argtypes, add.restype = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32], ctypes.c_int
            fd = init(os.O_NONBLOCK | os.O_CLOEXEC)
            if fd < 0:
                raise OSError(ctypes.get_errno(), 'inotify_init1')
            # MODIFY, ATTRIB, CLOSE_WRITE, MOVED_FROM/TO, CREATE, DELETE,
            # DELETE_SELF, MOVE_SELF. IN_Q_OVERFLOW is delivered automatically.
            mask = 0x2 | 0x4 | 0x8 | 0x40 | 0x80 | 0x100 | 0x200 | 0x400 | 0x800
            if add(fd, os.fsencode(self.payload), mask) < 0:
                error = ctypes.get_errno()
                os.close(fd)
                raise OSError(error, 'inotify_add_watch')
            self.inotify_fd = fd
        except Exception as exc:
            self.inotify_error = type(exc).__name__ + ': ' + str(exc)
        self.thread = threading.Thread(target=self._run, name='bs-read-only-file-monitor', daemon=True)

    def _keep(self, target, value):
        if len(target) < MAX_EVENTS:
            target.append(value)
        else:
            self.dropped += 1

    def _violation(self, kind, name, before, after):
        self._keep(self.violations, {'kind': kind, 'name': name,
                                    'before': before, 'after': after,
                                    'elapsed_seconds': time.monotonic() - self.start})

    def snapshot(self, tag):
        with self.lock:
            current = {}
            for path in sorted(self.payload.iterdir()):
                if path.suffix != '.jsonl' and not path.name.endswith('.jsonl.pending'):
                    continue
                try:
                    value = file_info(path.stat(follow_symlinks=False))
                except FileNotFoundError:
                    continue
                current[path.name] = value
                old = self.last.get(path.name)
                if old:
                    if (old['device'], old['inode']) != (value['device'], value['inode']):
                        self._violation('PATH_REPLACED', path.name, old, value)
                    elif value['size'] < old['size']:
                        self._violation('SIZE_REGRESSION', path.name, old, value)
                closed = self.closed.get(path.name)
                if closed and closed != value:
                    self._violation('CLOSED_FILE_CHANGED', path.name, closed, value)
                identity = (value['device'], value['inode'])
                if identity not in self.held:
                    if len(self.held) >= 8:
                        self._violation('DESCRIPTOR_CAP', path.name, None, value)
                    else:
                        try:
                            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                            opened = file_info(os.fstat(fd))
                            opened_identity = (opened['device'], opened['inode'])
                            if opened_identity != identity:
                                self._violation('PATH_OPEN_RACE', path.name, value, opened)
                            if opened_identity in self.held:
                                os.close(fd)
                            else:
                                self.held[opened_identity] = (fd, path.name)
                        except FileNotFoundError:
                            pass
            for name, closed in self.closed.items():
                if name not in current:
                    self._violation('CLOSED_FILE_MISSING', name, closed, None)
            descriptors = []
            for identity, (fd, name) in self.held.items():
                descriptors.append({'first_name': name, **file_info(os.fstat(fd))})
            previous_visible = getattr(self, 'last_visible', {})
            changed = current != previous_visible
            if changed or tag != 'poll':
                self._keep(self.samples, {'tag': tag, 'elapsed_seconds': time.monotonic()-self.start,
                                         'paths': current, 'held_descriptors': descriptors})
            # Keep disappeared identities in last to detect replacement if a
            # path reappears. Pending unlink after successful BR publication is
            # recorded, but is not itself an integrity failure.
            self.last.update(current)
            self.last_visible = current
            self._drain_inotify()
            return {'paths': current, 'held_descriptors': descriptors}

    def _drain_inotify(self):
        if self.inotify_fd is None:
            return
        while True:
            try:
                data = os.read(self.inotify_fd, 65536)
            except BlockingIOError:
                return
            if not data:
                return
            offset = 0
            while offset < len(data):
                wd, mask, cookie, length = struct.unpack_from('iIII', data, offset)
                offset += 16
                name = data[offset:offset+length].split(b'\0', 1)[0].decode('utf-8', 'replace')
                offset += length
                self._keep(self.events, {'elapsed_seconds': time.monotonic()-self.start,
                                         'mask': mask, 'cookie': cookie, 'name': name})
                if mask & 0x4000:
                    self._violation('INOTIFY_OVERFLOW', name, None, None)

    def mark_closed(self, path):
        with self.lock:
            self.closed[Path(path).name] = file_info(Path(path).stat(follow_symlinks=False))
            self.snapshot('closed:' + Path(path).name)

    def _run(self):
        try:
            while not self.stop_event.wait(.02):
                self.snapshot('poll')
        except BaseException as exc:
            self.errors.append(type(exc).__name__ + ': ' + str(exc))

    def begin(self):
        self.thread.start()

    def finish(self):
        self.stop_event.set()
        self.thread.join(timeout=3)
        if self.thread.is_alive():
            raise RuntimeError('Read-only monitor did not terminate')
        self.snapshot('final')
        with self.lock:
            result = {'schema': 'BS_READ_ONLY_FILE_MONITOR_V1',
                      'interval_seconds': .02, 'inotify_available': self.inotify_fd is not None,
                      'inotify_error': self.inotify_error, 'samples': self.samples,
                      'inotify_events': self.events, 'violations': self.violations,
                      'monitor_errors': self.errors, 'dropped_events': self.dropped,
                      'complete': not self.errors and self.dropped == 0,
                      'limitations': 'Point-in-time observations; not process attribution or proof of future stability.'}
            for fd, _ in self.held.values():
                os.close(fd)
            if self.inotify_fd is not None:
                os.close(self.inotify_fd)
            return result


def verify_file(path, expected):
    """Independent constant-memory byte/hash/JSON record check."""
    path = Path(path)
    start = file_info(path.stat(follow_symlinks=False))
    digest, byte_count, records = hashlib.sha256(), 0, 0
    with path.open('rb') as stream:
        fd_start = file_info(os.fstat(stream.fileno()))
        for line in stream:
            if not line.endswith(b'\n'):
                raise ValueError('Truncated fixture JSONL record')
            record = json.loads(line)
            if record != fixture_record(expected['stream'], records):
                raise ValueError('Fixture record differs at index ' + str(records))
            digest.update(line)
            byte_count += len(line)
            records += 1
        fd_end = file_info(os.fstat(stream.fileno()))
    end = file_info(path.stat(follow_symlinks=False))
    actual = {'path': path.name, 'bytes': byte_count, 'sha256': digest.hexdigest(),
              'records': records, 'complete': True}
    if start != fd_start or start != fd_end or start != end:
        raise ValueError('Fixture identity changed during independent verification')
    if any(actual[k] != expected[k] for k in ('bytes', 'sha256', 'records')):
        raise ValueError('Fixture receipt differs from independent expected bytes')
    return {**actual, 'identity': end}


def save_json(path, value):
    payload = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
    with Path(path).open('xb') as stream:
        if stream.write(payload) != len(payload):
            raise ValueError('Short evidence write')
        stream.flush()
        os.fsync(stream.fileno())
    if sha(path) != hashlib.sha256(payload).hexdigest():
        raise ValueError('Evidence changed after write')
    return {'path': Path(path).name, 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}


def run_fixture(kind, output_dir, records=MAX_RECORDS, pace_ms=0, emit=False):
    if kind not in SOURCE_PINS or not isinstance(records, int) or not 1 <= records <= MAX_RECORDS:
        raise ValueError('Invalid fixed fixture configuration')
    if not 0 <= pace_ms <= 100:
        raise ValueError('Pace must be within fixed 0..100 ms cap')
    output = Path(output_dir).resolve()
    output.mkdir(parents=False, exist_ok=False)
    payload = output / 'payload'
    payload.mkdir()
    started = time.monotonic()
    module, source = load_writer(kind)
    monitor = LifecycleMonitor(payload)
    monitor.begin()
    result = {'schema': 'SETI_BS_FILE_DIAGNOSTIC_V1', 'status': 'RUNNING', 'writer': kind,
              'records_per_stream': records, 'streams': [], 'pace_ms_per_1000_records': pace_ms,
              'source_pin': source, 'new_RNG_calls': 0, 'new_scan_scores': 0,
              'astronomical_powers_opened': 0, 'actual_scientific_input_files_opened': 0,
              'inherited_or_tightened_resource_limits': {
                  name: list(resource.getrlimit(getattr(resource, name)))
                  for name in ('RLIMIT_CPU', 'RLIMIT_AS', 'RLIMIT_FSIZE')}}
    error = None
    try:
        for index in range(2):
            path = payload / ('fixture_%d.jsonl' % index)
            writer = module.AssociationWriter(path) if kind == 'bq' else module.AtomicJSONLPublisher(payload, path.name)
            digest, byte_count = hashlib.sha256(), 0
            detail = {'stream': index, 'path': path.name, 'status': 'RUNNING'}
            result['streams'].append(detail)
            try:
                for number in range(records):
                    record = fixture_record(index, number)
                    raw = encode(record)
                    digest.update(raw)
                    byte_count += len(raw)
                    writer.append(record)
                    if (number+1) % 1000 == 0:
                        if time.monotonic()-started > 180:
                            raise TimeoutError('Fixed 180 second wall deadline exceeded')
                        if pace_ms:
                            time.sleep(pace_ms / 1000.)
                    if emit and (number+1) % 10000 == 0:
                        print(json.dumps({'event': 'BS_PROGRESS', 'writer': kind, 'stream': index,
                                          'records_written': number+1,
                                          'elapsed_seconds': time.monotonic()-started}), flush=True)
                expected = {'path': path.name, 'stream': index, 'bytes': byte_count,
                            'records': records, 'sha256': digest.hexdigest(), 'complete': True}
                detail['expected'] = expected
                detail['before_close'] = monitor.snapshot('before_close:' + path.name)
                detail['writer_fd_before_close'] = file_info(os.fstat(writer.stream.fileno()))
                detail['writer_receipt'] = writer.close()
                detail['after_close'] = monitor.snapshot('after_close:' + path.name)
                if any(detail['writer_receipt'][k] != expected[k]
                       for k in ('path', 'bytes', 'records', 'sha256', 'complete')):
                    raise ValueError('Writer receipt differs from separately encoded fixture')
                monitor.mark_closed(path)
                detail['initial_independent_check'] = verify_file(path, expected)
                detail['status'] = 'PASS'
            except BaseException as exc:
                detail['status'] = 'FAIL'
                detail['exception'] = type(exc).__name__ + ': ' + str(exc)
                detail['exception_code'] = getattr(exc, 'code', None)
                detail['after_exception'] = monitor.snapshot('exception:' + path.name)
                try:
                    writer.close_partial()
                except BaseException as cleanup_exc:
                    detail['cleanup_exception'] = type(cleanup_exc).__name__ + ': ' + str(cleanup_exc)
                raise
        for detail in result['streams']:
            detail['final_independent_check'] = verify_file(payload/detail['path'], detail['expected'])
            if detail['initial_independent_check'] != detail['final_independent_check']:
                raise ValueError('Closed stream changed between independent checks')
        if sha(REPO/source['path']) != source['sha256']:
            raise ValueError('Writer source changed during run')
        result['status'] = 'PASS'
    except BaseException as exc:
        result['status'] = 'FAIL'
        error = {'exception': type(exc).__name__ + ': ' + str(exc),
                 'exception_code': getattr(exc, 'code', None), 'traceback': traceback.format_exc()}
    finally:
        observation = monitor.finish()
    if observation['violations'] or not observation['complete']:
        result['status'] = 'FAIL'
    result.update(error=error, monitor=save_json(output/'FILE_MONITOR.json', observation),
                  monitor_complete=observation['complete'], monitor_violations=len(observation['violations']),
                  inotify_available=observation['inotify_available'],
                  wall_seconds=time.monotonic()-started,
                  max_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                  scientific_qualification='Engineering fixture only; no A04 qualification or SETI claim.')
    saved = save_json(output/'RESULT.json', result)
    if emit:
        print(json.dumps({'event': 'GATE_TERMINAL_EOF', 'status': result['status'],
                          'result_sha256': saved['sha256']}), flush=True)
    return result


def tighten_limit(which, desired):
    """Never relax a caller's finite soft or hard resource limit."""
    soft, hard = resource.getrlimit(which)
    new_hard = desired if hard == resource.RLIM_INFINITY else min(desired, hard)
    new_soft = new_hard if soft == resource.RLIM_INFINITY else min(new_hard, soft)
    resource.setrlimit(which, (new_soft, new_hard))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--writer', required=True, choices=tuple(SOURCE_PINS))
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--records', type=int, default=MAX_RECORDS)
    parser.add_argument('--pace-ms', type=int, default=0)
    args = parser.parse_args()
    tighten_limit(resource.RLIMIT_CPU, 180)
    tighten_limit(resource.RLIMIT_AS, 512*1024*1024)
    tighten_limit(resource.RLIMIT_FSIZE, 256*1024*1024)
    result = run_fixture(args.writer, args.output_dir, args.records, args.pace_ms, emit=True)
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
