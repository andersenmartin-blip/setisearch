#!/usr/bin/env python3
"""Two-call streaming caller-tail custody, with raw/noecho before READY.

Only a bounded compact JSON transfer is accepted on stdin. The authoritative
file retains the existing ASCII canonical tail, independently reopened/hash
verified after both file and directory fsync. No retry or authority is granted.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import select
import stat
import sys
import termios
import time
import tty

READY_SCHEMA = 'radio-native-v2-streaming-caller-tail-ready-v1'
READBACK_SCHEMA = 'radio-native-v2-streaming-caller-tail-readback-v1'
TAIL_SCHEMA = 'radio-native-v2-caller-only-tail-v2'
MAX_RECORDS = 7
MAX_ENVELOPE_BYTES = 256 * 1024
MAX_RAW_BYTES = MAX_RECORDS * MAX_ENVELOPE_BYTES
MAX_WIRE_BYTES = 2 * MAX_RAW_BYTES + 2048
MAX_BASE64_BYTES = ((MAX_WIRE_BYTES + 2) // 3) * 4
MAX_CANONICAL_BYTES = 6 * MAX_RAW_BYTES + 2048
AUTHORITY = {'execution_authorized': False, 'reservation_authorized': False,
    'scientific_execution_authorized': False, 'automatic_retry': False,
    'rng_draws': 0, 'telescope_reads': 0}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _open_parent(destination):
    if (type(destination) is not str or len(destination) > 4096
            or not re.fullmatch('/[A-Za-z0-9_./-]+', destination)
            or any(p in ('', '.', '..') for p in destination[1:].split('/'))):
        raise ValueError('Canonical absolute caller-tail destination required')
    parts = destination[1:].split('/')
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            fresh = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = fresh
        return directory, parts[-1]
    except BaseException:
        os.close(directory)
        raise


def validate_wire(wire, *, wire_bytes, wire_sha256, payload_bytes,
                  payload_sha256, client_sha256, terminal_ordinal):
    if (type(wire_bytes) is not int or not 0 < wire_bytes <= MAX_WIRE_BYTES
            or len(wire) != wire_bytes or sha(wire) != wire_sha256
            or type(payload_bytes) is not int or not 0 < payload_bytes <= MAX_CANONICAL_BYTES
            or not re.fullmatch('[0-9a-f]{64}', client_sha256)
            or type(terminal_ordinal) is not int or terminal_ordinal < 0):
        raise ValueError('Exact bounded streaming tail pins required')
    value = json.loads(wire)
    if (type(value) is not dict or set(value) != {'schema', 'client_sha256', 'records'}
            or value['schema'] != TAIL_SCHEMA or value['client_sha256'] != client_sha256
            or type(value['records']) is not list or not 1 <= len(value['records']) <= MAX_RECORDS):
        raise ValueError('Exact compact caller-only tail required')
    previous, raw_bytes, acknowledged = -1, 0, False
    for row in value['records']:
        if (type(row) is not dict or set(row) != {'ordinal', 'response_json'}
                or type(row['ordinal']) is not int or row['ordinal'] <= previous
                or type(row['response_json']) is not str):
            raise ValueError('Exact ordered streaming tail envelopes required')
        size = len(row['response_json'].encode())
        if size > MAX_ENVELOPE_BYTES:
            raise ValueError('Caller-only raw reply exceeds unchanged envelope cap')
        raw_bytes += size
        result = json.loads(row['response_json'])
        if type(result) is not dict:
            raise ValueError('Complete raw execution envelope required')
        if row['ordinal'] == terminal_ordinal:
            if result.get('isError') is True or type(result.get('output')) is not str:
                raise ValueError('Complete final delivery acknowledgement required')
            acknowledged = True
        previous = row['ordinal']
    if raw_bytes > MAX_RAW_BYTES or not acknowledged:
        raise ValueError('Bounded final delivery acknowledgement required')
    payload = canonical(value)
    if len(payload) != payload_bytes or sha(payload) != payload_sha256:
        raise ValueError('Independent canonical streaming tail pin differs')
    return payload, [r['ordinal'] for r in value['records']]


def persist_tail(destination, payload):
    """Exclusive creation and a fresh nofollow readback; preserve failed bytes."""
    directory, basename = _open_parent(destination)
    try:
        original_parent = os.fstat(directory)
        writer = os.open(basename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600, dir_fd=directory)
        try:
            created = os.fstat(writer)
            if not stat.S_ISREG(created.st_mode) or created.st_nlink != 1:
                raise ValueError('One authoritative regular streaming tail required')
            cursor = 0
            while cursor < len(payload):
                count = os.write(writer, memoryview(payload)[cursor:])
                if count <= 0:
                    raise OSError('Streaming tail write made no progress')
                cursor += count
            os.fsync(writer)
        finally:
            os.close(writer)
        os.fsync(directory)
        reader = os.open(basename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:
            opened = os.fstat(reader)
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_size != len(payload)
                    or (opened.st_dev, opened.st_ino) != (created.st_dev, created.st_ino)):
                raise ValueError('Independent streaming tail readback identity changed')
            digest, size = hashlib.sha256(), 0
            while True:
                block = os.read(reader, min(65536, len(payload) + 1 - size))
                if not block:
                    break
                size += len(block)
                if size > len(payload):
                    raise ValueError('Independent streaming tail readback grew')
                digest.update(block)
            after = os.fstat(reader)
            if (size != len(payload) or digest.hexdigest() != sha(payload) or after.st_nlink != 1
                    or (after.st_size, after.st_mtime_ns, after.st_ctime_ns) !=
                    (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)):
                raise ValueError('Independent streaming tail readback bytes changed')
        finally:
            os.close(reader)
        fresh_parent, fresh_basename = _open_parent(destination)
        try:
            fresh = os.fstat(fresh_parent)
            if (fresh.st_dev, fresh.st_ino) != (original_parent.st_dev, original_parent.st_ino):
                raise ValueError('Authoritative streaming tail parent path changed')
            current = os.stat(fresh_basename, dir_fd=fresh_parent, follow_symlinks=False)
            if (current.st_nlink != 1 or (current.st_dev, current.st_ino, current.st_size,
                    current.st_mtime_ns, current.st_ctime_ns) != (after.st_dev, after.st_ino,
                    after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
                raise ValueError('Authoritative streaming tail path changed')
        finally:
            os.close(fresh_parent)
        return {'reopened_bytes': size, 'reopened_sha256': digest.hexdigest(),
            'durable': True, 'single_authoritative_file': True, 'exact_readback_verified': True,
            'directory_entry_fsynced': True, 'independent_reopen': True}
    finally:
        os.close(directory)


def read_transfer(fd, *, seconds=600):
    """Bound partial stdin as well as a missing first byte by one deadline."""
    deadline, pieces, size = time.monotonic() + seconds, [], 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            raise TimeoutError('Streaming stdin deadline exhausted; no retry')
        part = os.read(fd, min(65536, MAX_BASE64_BYTES + 2 - size))
        if not part:
            raise ValueError('Streaming stdin ended before a complete bounded line')
        pieces.append(part)
        size += len(part)
        if size > MAX_BASE64_BYTES + 1:
            raise ValueError('Streaming stdin exceeds its prospective bound')
        if b'\n' in part:
            line = b''.join(pieces)
            if not line.endswith(b'\n') or line.count(b'\n') != 1:
                raise ValueError('Exactly one streaming base64 line required')
            return line[:-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True)
    parser.add_argument('--wire-bytes', required=True, type=int)
    parser.add_argument('--wire-sha256', required=True)
    parser.add_argument('--payload-bytes', required=True, type=int)
    parser.add_argument('--payload-sha256', required=True)
    parser.add_argument('--client-sha256', required=True)
    parser.add_argument('--terminal-ordinal', required=True, type=int)
    parser.add_argument('--pipe-mode-component', action='store_true')
    args = parser.parse_args()
    original_tty = None
    try:
        if not (0 < args.wire_bytes <= MAX_WIRE_BYTES and 0 < args.payload_bytes <= MAX_CANONICAL_BYTES):
            raise ValueError('Prospective streaming input/output bounds required')
        for pin in (args.wire_sha256, args.payload_sha256, args.client_sha256):
            if not re.fullmatch('[0-9a-f]{64}', pin):
                raise ValueError('Exact streaming SHA256 pins required')
        directory, basename = _open_parent(args.destination)
        os.close(directory)
        stdin_is_tty = os.isatty(sys.stdin.fileno())
        if not stdin_is_tty and not args.pipe_mode_component:
            raise ValueError('Actual streaming startup requires a TTY for verified raw/noecho mode')
        if stdin_is_tty:
            original_tty = termios.tcgetattr(sys.stdin.fileno())
            tty.setraw(sys.stdin.fileno(), termios.TCSANOW)
        ready = {'schema': READY_SCHEMA, 'kind': 'ready', 'destination': args.destination,
            'wire_bytes': args.wire_bytes, 'wire_sha256': args.wire_sha256,
            'payload_bytes': args.payload_bytes, 'payload_sha256': args.payload_sha256,
            'client_sha256': args.client_sha256, 'input_encoding': 'base64_utf8_json',
            'terminal_ordinal': args.terminal_ordinal,
            'maximum_base64_bytes': MAX_BASE64_BYTES, 'max_stdin_bytes': MAX_BASE64_BYTES + 1,
            'stdin_is_tty': stdin_is_tty, 'stdin_mode': 'tty_raw_noecho' if stdin_is_tty else 'pipe_noecho',
            'stdin_raw_noecho_ready': stdin_is_tty, **AUTHORITY}
        print(canonical(ready).decode(), flush=True)
        encoded = read_transfer(sys.stdin.fileno())
        wire = base64.b64decode(encoded, validate=True)
        if base64.b64encode(wire) != encoded:
            raise ValueError('Canonical streaming base64 transfer required')
        payload, ordinals = validate_wire(wire, wire_bytes=args.wire_bytes, wire_sha256=args.wire_sha256,
            payload_bytes=args.payload_bytes, payload_sha256=args.payload_sha256,
            client_sha256=args.client_sha256, terminal_ordinal=args.terminal_ordinal)
        custody = persist_tail(args.destination, payload)
        print(canonical({'schema': READBACK_SCHEMA, 'destination': args.destination,
            'client_sha256': args.client_sha256, 'stored_record_ordinals': ordinals,
            'payload_bytes': len(payload), 'payload_sha256': args.payload_sha256,
            'wire_bytes': len(wire), 'wire_sha256': args.wire_sha256,
            'includes_terminal_delivery_acknowledgement': True, **custody, **AUTHORITY}).decode(), flush=True)
        return 0
    except Exception as error:
        print(canonical({'schema': READBACK_SCHEMA, 'status': 'CLOSED_FAILED', 'error': str(error),
            'durable': False, **AUTHORITY}).decode(), flush=True)
        return 1
    finally:
        if original_tty is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, original_tty)


if __name__ == '__main__':
    sys.exit(main())
