"""Prospective bounded diagnostic retention; never a control qualification.

This standalone utility does not import or alter any frozen control recipe.
It captures bounded raw pipe prefixes and preserves them even when a child
fails.  A new, disjoint, outside-repository directory is exclusively reserved
before launch.  Existing destinations are never reopened or overwritten.
The retained JSON includes base64 reconstruction evidence, not a lossy UTF-8
rendering.  Missing historical bytes cannot be recovered from their hashes.

This is a diagnostic process wrapper, not a sandbox or a qualified whole-tree
lifetime observer.  Commands and independent destination/protected-root inputs
must be chosen by the caller.  The returned disposition and its persistence
proof must both pass; a zero child exit alone is insufficient.
"""
from dataclasses import dataclass
import base64
import errno
import hashlib
import json
import os
import selectors
import signal
import stat
import subprocess
import time

SCHEMA = 'radio-prospective-failure-output-retention-v1'
MAX_STREAM_CAP = 1024 * 1024
MAX_TIMEOUT_SECONDS = 4800
FILES = ('stdout.raw', 'stderr.raw', 'disposition.json')
# This selected helper's repository is forbidden even if a caller supplies a
# different synthetic repository_root. Additional historical/private roots must
# still come from the independently chosen invocation inputs.
IMPLEMENTATION_REPOSITORY_ROOT = os.path.dirname(os.path.dirname(__file__))


class RetentionError(ValueError):
    """Admission failed before launch; no destination may be reused."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii') + b'\n'


def _path(value):
    if (type(value) is not str or len(value) > 4096 or not value.startswith('/') or value == '/' or
            value != os.path.normpath(value) or '\\' in value or
            any(ord(c) < 32 for c in value) or
            any(p in ('', '.', '..') for p in value.split('/')[1:])):
        raise RetentionError('Exact canonical absolute path required')
    return value


def _overlap(left, right):
    return left == right or left.startswith(right + '/') or right.startswith(left + '/')


def _reserve(destination, repository_root, protected_roots):
    destination = _path(destination)
    roots = [_path(IMPLEMENTATION_REPOSITORY_ROOT), _path(repository_root)] + [_path(p) for p in protected_roots]
    if any(_overlap(destination, root) for root in roots):
        raise RetentionError('Destination overlaps repository or protected root')
    # Open every existing ancestor through held O_NOFOLLOW directory descriptors.
    # No mkdir -p, realpath following, overwrite, or rollback/rearm is permitted.
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    parent = os.open('/', flags)
    child = None
    try:
        parts = destination.split('/')[1:]
        for name in parts[:-1]:
            next_fd = os.open(name, flags, dir_fd=parent)
            os.close(parent)
            parent = next_fd
        os.mkdir(parts[-1], 0o700, dir_fd=parent)
        child = os.open(parts[-1], flags, dir_fd=parent)
        here = os.fstat(child)
        visible = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
        if (not stat.S_ISDIR(here.st_mode) or
                (here.st_dev, here.st_ino) != (visible.st_dev, visible.st_ino)):
            raise RetentionError('Exclusive destination identity changed')
        os.fsync(parent)
        fds = {}
        try:
            for name in FILES:
                fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL |
                             os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=child)
                fds[name] = fd
                s = os.fstat(fd)
                if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1:
                    raise RetentionError('Exclusive ordinary single-link output required')
        except BaseException:
            for fd in fds.values():
                os.close(fd)
            raise
        os.fsync(child)
        result = (child, fds, {'path': destination, 'device': here.st_dev,
                              'inode': here.st_ino, 'exclusively_created': True})
        child = None
        return result
    except (OSError, ValueError) as error:
        raise RetentionError('Exclusive outside-repository reservation failed: ' + str(error)) from error
    finally:
        if child is not None:
            os.close(child)
        os.close(parent)


def _write_all(fd, data):
    offset = 0
    while offset < len(data):
        count = os.write(fd, data[offset:])
        if count <= 0:
            raise OSError(errno.EIO, 'Short diagnostic write')
        offset += count


def _snapshot(fd, bound):
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > bound:
        raise RetentionError('Output identity, link count, or bound changed')
    os.lseek(fd, 0, os.SEEK_SET)
    pieces = []
    remaining = before.st_size
    while remaining:
        block = os.read(fd, min(65536, remaining))
        if not block:
            raise RetentionError('Output changed during held readback')
        pieces.append(block)
        remaining -= len(block)
    after = os.fstat(fd)
    if (before.st_dev, before.st_ino, before.st_nlink, before.st_size,
            before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_dev, after.st_ino, after.st_nlink, after.st_size,
            after.st_mtime_ns, after.st_ctime_ns):
        raise RetentionError('Output metadata changed during held readback')
    raw = b''.join(pieces)
    return raw, {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                 'device': after.st_dev, 'inode': after.st_ino, 'links': after.st_nlink}


def _match_files(directory, fds):
    for name, fd in fds.items():
        held = os.fstat(fd)
        current = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if (not stat.S_ISREG(current.st_mode) or held.st_nlink != 1 or current.st_nlink != 1 or
                (held.st_dev, held.st_ino) != (current.st_dev, current.st_ino)):
            raise RetentionError('Output pathname or single-link identity changed')


def reconstruct_raw(evidence):
    """Reconstruct only the retained raw bytes, checking size and SHA256."""
    if (type(evidence) is not dict or set(evidence) != {'encoding', 'bytes', 'sha256', 'data'} or
            evidence['encoding'] != 'base64' or type(evidence['bytes']) is not int or
            not 0 <= evidence['bytes'] <= MAX_STREAM_CAP or type(evidence['data']) is not str or
            len(evidence['data']) > 4*((MAX_STREAM_CAP+2)//3) or
            type(evidence['sha256']) is not str):
        raise RetentionError('Exact bounded raw reconstruction evidence required')
    try:
        raw = base64.b64decode(evidence['data'].encode('ascii'), validate=True)
    except (UnicodeError, ValueError) as error:
        raise RetentionError('Invalid raw base64 reconstruction') from error
    if (len(raw) != evidence['bytes'] or hashlib.sha256(raw).hexdigest() != evidence['sha256'] or
            base64.b64encode(raw).decode('ascii') != evidence['data']):
        raise RetentionError('Raw reconstruction differs from retained size/hash')
    return raw


def _evidence(raw):
    return {'encoding': 'base64', 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(),
            'data': base64.b64encode(raw).decode('ascii')}


@dataclass(frozen=True)
class CaptureResult:
    payload: bytes
    disposition_payload: bytes

    def record(self):
        return json.loads(self.payload)


def capture(argv, *, destination, repository_root, protected_roots=(),
            stdout_cap=65536, stderr_cap=65536, timeout_seconds=10, env=None):
    """Launch once, retain bounded raw diagnostics, and emit one disposition.

    A cap breach terminates the child and marks the complete stream length
    unknown.  Failed writes remain failed; no output is overwritten to repair
    or promote a disposition.  CaptureResult separates the immutable first
    disposition from its final held-file persistence proof.
    """
    if (type(argv) not in (list, tuple) or not 0 < len(argv) <= 128 or
            any(type(x) is not str or not x or len(x) > 4096 or '\x00' in x for x in argv) or
            sum(len(x) for x in argv) > 32768 or
            any(type(cap) is not int or not 0 <= cap <= MAX_STREAM_CAP
                for cap in (stdout_cap, stderr_cap)) or
            type(timeout_seconds) not in (int, float) or
            not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS or
            type(protected_roots) not in (list, tuple)):
        raise RetentionError('Exact bounded command/cap/timeout inputs required')
    directory, fds, identity = _reserve(destination, repository_root, protected_roots)
    buffers = {'stdout': bytearray(), 'stderr': bytearray()}
    caps = {'stdout': stdout_cap, 'stderr': stderr_cap}
    observed = {'stdout': 0, 'stderr': 0}
    eof = {'stdout': False, 'stderr': False}
    child = None
    selector = selectors.DefaultSelector()
    timed_out = exceeded = False
    capture_error = None
    launch_error = None
    started = time.monotonic()
    stop_at = started + timeout_seconds
    drain_until = None
    killed = False
    try:
        try:
            child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, close_fds=True,
                                     start_new_session=True, env=env)
            for name, stream in (('stdout', child.stdout), ('stderr', child.stderr)):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map():
                now = time.monotonic()
                if now >= stop_at and not killed:
                    timed_out = True
                if (timed_out or exceeded or capture_error) and not killed:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    killed = True
                    drain_until = now + 0.5
                if killed and now >= drain_until:
                    break
                for key, _ in selector.select(min(0.05, max(0, (drain_until if killed else stop_at)-now))):
                    block = os.read(key.fileobj.fileno(), 65536)
                    name = key.data
                    if not block:
                        eof[name] = True
                        selector.unregister(key.fileobj)
                        continue
                    observed[name] += len(block)
                    available = max(0, caps[name] - len(buffers[name]))
                    buffers[name].extend(block[:available])
                    if observed[name] > caps[name]:
                        exceeded = True
            if not killed and child.poll() is None:
                try:
                    child.wait(timeout=max(0.001, stop_at-time.monotonic()))
                except subprocess.TimeoutExpired:
                    timed_out = True
                    os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=2)
            if time.monotonic() >= stop_at:
                timed_out = True
        except OSError as error:
            if child is None:
                launch_error = str(error)
            else:
                capture_error = str(error)
        except BaseException as error:
            capture_error = type(error).__name__ + ': ' + str(error)
        finally:
            if child is not None and child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    capture_error = 'Child did not reap within diagnostic cleanup bound'
            selector.close()
            if child is not None:
                child.stdout.close()
                child.stderr.close()
        process_status = ('LAUNCH_FAILURE' if launch_error else 'CAPTURE_FAILURE' if capture_error else
                          'TIMEOUT' if timed_out else 'OUTPUT_LIMIT' if exceeded else
                          'EXIT_ZERO' if child.returncode == 0 else 'EXIT_NONZERO')
        persistence_errors = []
        streams = {}
        for name in ('stdout', 'stderr'):
            raw = bytes(buffers[name])
            fd = fds[name+'.raw']
            write_complete = synced = False
            artifact = None
            try:
                _write_all(fd, raw)
                write_complete = True
                os.fsync(fd)
                synced = True
                os.fchmod(fd, 0o400)
                actual, artifact = _snapshot(fd, caps[name])
                if actual != raw:
                    raise RetentionError('Diagnostic file differs from exact retained raw prefix')
            except BaseException as error:
                persistence_errors.append({'file': name+'.raw', 'error': type(error).__name__+': '+str(error)})
                try:
                    actual, artifact = _snapshot(fd, caps[name])
                except BaseException:
                    artifact = None
            streams[name] = {'cap_bytes': caps[name], 'observed_bytes': observed[name],
                             'eof_observed': eof[name], 'truncated': observed[name] > caps[name] or not eof[name],
                             'full_stream_retained': eof[name] and observed[name] <= caps[name],
                             'file': name+'.raw', 'file_pin': artifact,
                             'file_write_complete': write_complete, 'file_fsync_complete': synced,
                             'reconstruction': _evidence(raw)}
        disposition = {'schema': SCHEMA, 'authority': 'future-diagnostic-utility-only',
                       'destination': identity, 'argv': list(argv),
                       'process_status': process_status, 'returncode': None if child is None else child.returncode,
                       'child_reaped': child is not None and child.returncode is not None,
                       'timeout_seconds': timeout_seconds, 'timed_out': timed_out,
                       'output_limit_exceeded': exceeded, 'launch_error': launch_error,
                       'capture_error': capture_error, 'streams': streams,
                       'persistence_errors': persistence_errors,
                       'strictly_completed': process_status == 'EXIT_ZERO' and not persistence_errors,
                       'automatic_retry': False, 'overwrites_performed': False,
                       'whole_descendant_lifetime_qualified': False,
                       'scientific_execution_authorized': False,
                       'engineering_control_qualified': False,
                       'historical_lost_output_reconstructed': False}
        first_payload = canonical(disposition)
        if len(first_payload) > 4*MAX_STREAM_CAP:
            raise RetentionError('Bounded diagnostic disposition capacity exceeded')
        manifest_complete = manifest_synced = False
        manifest_pin = None
        try:
            _write_all(fds['disposition.json'], first_payload)
            manifest_complete = True
            os.fsync(fds['disposition.json'])
            manifest_synced = True
            os.fchmod(fds['disposition.json'], 0o400)
            actual, manifest_pin = _snapshot(fds['disposition.json'], 4*MAX_STREAM_CAP)
            if actual != first_payload:
                raise RetentionError('Disposition differs from first exact terminal record')
            os.fsync(directory)
            _match_files(directory, fds)
        except BaseException as error:
            persistence_errors = persistence_errors + [{'file': 'disposition.json',
                                                       'error': type(error).__name__+': '+str(error)}]
            try:
                _, manifest_pin = _snapshot(fds['disposition.json'], 4*MAX_STREAM_CAP)
            except BaseException:
                manifest_pin = None
        final = {**disposition, 'persistence_errors': persistence_errors,
                 'strictly_completed': disposition['strictly_completed'] and not persistence_errors,
                 'disposition_file_pin': manifest_pin,
                 'disposition_write_complete': manifest_complete,
                 'disposition_fsync_complete': manifest_synced,
                 'disposition_first_payload_sha256': hashlib.sha256(first_payload).hexdigest()}
        return CaptureResult(canonical(final), first_payload)
    finally:
        selector.close()
        for fd in fds.values():
            os.close(fd)
        os.close(directory)
