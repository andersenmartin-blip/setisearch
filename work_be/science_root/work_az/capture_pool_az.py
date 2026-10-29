"""Parent-owned byte capture for concurrent child processes; no science logic.

Each child has one stdout PIPE (stderr merged). Only this parent writes the
private log. EOF, process exit, flush/fsync and exact stream/file hash agreement
precede publication of the final log and the caller's exit receipt. No retry.
"""
from pathlib import Path
import datetime
import hashlib
import os
import selectors
import subprocess
import time


class CapturePoolFailure(RuntimeError):
    def __init__(self, failure, records):
        super().__init__(str(failure))
        self.failure = failure
        self.records = records


def run_capture_pool(commands, log_directory, *, max_workers=6,
                     sample_interval=.2, guard=lambda: None,
                     on_launch=lambda j: None, on_closed=lambda r: None,
                     terminate_grace_seconds=5.):
    """Run ordered (scan, argv) commands and return records sorted by scan.

    A failed child or parent guard stops new launches and terminates live peers.
    Pipes are still drained to EOF. Unresponsive peers are killed after the
    bounded termination grace. Successful/failed logs are never repaired.
    """
    commands = list(commands)
    assert len({j for j, _ in commands}) == len(commands)
    assert max_workers > 0 and sample_interval > 0
    folder = Path(log_directory)
    folder.mkdir(parents=True, exist_ok=True)
    pending = list(commands)
    running = {}
    closed = []
    selector = selectors.DefaultSelector()
    failure = None
    abort_started = None
    next_guard = 0.

    def abort(reason):
        nonlocal failure, abort_started
        if failure is None:
            failure = reason
            abort_started = time.monotonic()
            pending.clear()
            for entry in running.values():
                if entry['process'].poll() is None:
                    entry['terminated_by_parent'] = True
                    entry['process'].terminate()

    def launch(j, argv):
        final = folder / f'scan{j}.log'
        private = folder / f'scan{j}.log.capture.part'
        assert not final.exists() and not private.exists()
        stream = private.open('xb')
        try:
            process = subprocess.Popen(list(argv), stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, bufsize=0,
                                       close_fds=True)
        except BaseException:
            stream.close()
            raise
        os.set_blocking(process.stdout.fileno(), False)
        entry = dict(scan=j, command=list(argv), process=process, stream=stream,
                     final=final, private=private, hasher=hashlib.sha256(),
                     received=0, eof=False, terminated_by_parent=False,
                     killed_after_grace=False)
        running[j] = entry
        selector.register(process.stdout, selectors.EVENT_READ, j)
        on_launch(j)

    def drain(events):
        for key, _ in events:
            entry = running[key.data]
            try:
                data = os.read(key.fileobj.fileno(), 65536)
            except BlockingIOError:
                continue
            if data:
                assert entry['stream'].write(data) == len(data)
                entry['hasher'].update(data)
                entry['received'] += len(data)
            else:
                selector.unregister(key.fileobj)
                key.fileobj.close()
                entry['eof'] = True

    def finish(j, entry):
        process = entry['process']
        assert entry['eof'] and process.poll() is not None
        code = process.wait()
        stream = entry['stream']
        stream.flush()
        os.fsync(stream.fileno())
        stream.close()
        size = entry['private'].stat().st_size
        with entry['private'].open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        assert size == entry['received'] and digest == entry['hasher'].hexdigest()
        assert not entry['final'].exists()
        os.replace(entry['private'], entry['final'])
        with entry['final'].open('rb') as source:
            assert hashlib.file_digest(source, 'sha256').hexdigest() == digest
        assert entry['final'].stat().st_size == size
        record = dict(scan=j, exit_code=code, command=entry['command'],
                      log=str(entry['final']), log_sha256=digest, log_bytes=size,
                      completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      pipe_EOF_before_log_publish=True,
                      parent_only_log_writer=True, log_flush_fsync_before_publish=True,
                      stream_file_byte_count_and_sha256_match=True,
                      stream_bytes_received=entry['received'],
                      terminated_by_parent=entry['terminated_by_parent'],
                      killed_after_termination_grace=entry['killed_after_grace'])
        closed.append(record)
        del running[j]
        on_closed(record)

    try:
        while pending or running:
            try:
                now = time.monotonic()
                if failure is None and now >= next_guard:
                    guard()
                    next_guard = time.monotonic() + sample_interval
                while failure is None and pending and len(running) < max_workers:
                    launch(*pending.pop(0))
                timeout = sample_interval if failure is not None else max(0., min(sample_interval, next_guard - time.monotonic()))
                drain(selector.select(timeout))
                for j, entry in list(running.items()):
                    code = entry['process'].poll()
                    if code is not None and code != 0:
                        abort(dict(kind='child_exit', scan=j, exit_code=code))
                if failure is not None and time.monotonic() - abort_started >= terminate_grace_seconds:
                    for entry in running.values():
                        if entry['process'].poll() is None:
                            entry['killed_after_grace'] = True
                            entry['process'].kill()
                for j, entry in list(running.items()):
                    if entry['eof'] and entry['process'].poll() is not None:
                        finish(j, entry)
            except BaseException as error:
                if failure is not None:
                    raise
                abort(dict(kind='parent_error', error=repr(error)))
    finally:
        # Exceptional I/O/receipt failures still stop and reap every child.
        for entry in running.values():
            process = entry['process']
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=terminate_grace_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            try:
                selector.unregister(process.stdout)
            except (KeyError, ValueError):
                pass
            process.stdout.close()
            if not entry['stream'].closed:
                entry['stream'].flush()
                os.fsync(entry['stream'].fileno())
                entry['stream'].close()
        selector.close()
    closed.sort(key=lambda record: record['scan'])
    if failure is not None:
        raise CapturePoolFailure(failure, closed)
    return closed
