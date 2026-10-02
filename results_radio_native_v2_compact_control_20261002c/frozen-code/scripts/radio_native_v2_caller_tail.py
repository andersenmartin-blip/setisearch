#!/usr/bin/env python3
"""Exclusive, independently reopened caller-tail custody; no execution authority.

The portable wrapper sends only the compact, already canonical tail. The caller
and the shared contract independently bind that tail to complete envelope hashes.
This helper has no connector, retry, science, overwrite, or import of repo code.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import stat
import sys

TAIL_SCHEMA = 'radio-native-v2-caller-only-tail-v2'
READBACK_SCHEMA = 'radio-native-v2-caller-tail-readback-v1'
MAX_BASE64_BYTES = 62 * 1024
MAX_PAYLOAD_BYTES = MAX_BASE64_BYTES // 4 * 3
AUTHORITY = {'execution_authorized': False, 'reservation_authorized': False,
             'scientific_execution_authorized': False, 'rng_draws': 0,
             'telescope_reads': 0, 'automatic_retry': False}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_payload(payload, *, expected_bytes, expected_sha256,
                     client_sha256, terminal_ordinal):
    """Validate bounded bytes and the exact terminal acknowledgement projection."""
    if (type(expected_bytes) is not int or not 0 < expected_bytes <= MAX_PAYLOAD_BYTES
            or len(payload) != expected_bytes or sha(payload) != expected_sha256
            or not re.fullmatch('[0-9a-f]{64}', client_sha256)
            or type(terminal_ordinal) is not int or terminal_ordinal < 0):
        raise ValueError('Exact bounded caller-tail bytes and client binding required')
    value = json.loads(payload)
    if (type(value) is not dict or set(value) != {'schema', 'client_sha256', 'records'}
            or value['schema'] != TAIL_SCHEMA or value['client_sha256'] != client_sha256
            or canonical(value) != payload):
        raise ValueError('Exact canonical caller-only tail required')
    records = value['records']
    if type(records) is not list or not records:
        raise ValueError('Terminal delivery acknowledgement required')
    previous = -1
    for row in records:
        if (type(row) is not dict or set(row) != {'ordinal', 'response_json'}
                or type(row['ordinal']) is not int or row['ordinal'] <= previous
                or type(row['response_json']) is not str):
            raise ValueError('Exact ordered caller-only raw envelopes required')
        restored = json.loads(row['response_json'])
        if type(restored) is not dict:
            raise ValueError('Complete raw execution envelope required')
        previous = row['ordinal']
    selected = next((row for row in records if row['ordinal'] == terminal_ordinal), None)
    if selected is None:
        raise ValueError('Terminal delivery acknowledgement absent')
    # The last delivery can acknowledge a still-running controller, whose
    # terminal frame arrives in a later poll (or is split between replies).
    # Its complete raw acknowledgement must be retained, not self-certified
    # by interpreting just that acknowledgement as the controller terminal.
    result = json.loads(selected['response_json'])
    if result.get('isError') is True or type(result.get('output')) is not str:
        raise ValueError('Complete terminal delivery acknowledgement required')
    return value


def _open_parent(destination):
    """Walk every absolute path component with no symlink following."""
    if (type(destination) is not str or not re.fullmatch('/[A-Za-z0-9_./-]+', destination)
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


def persist_tail(destination, payload, *, expected_bytes, expected_sha256,
                 client_sha256, terminal_ordinal):
    """Write once, fsync file and parent, then hash a fresh independent open.

    A failed operation leaves any already-created evidence in place. Retrying
    that path is refused by O_EXCL. The helper never deletes or replaces it.
    """
    value = validate_payload(payload, expected_bytes=expected_bytes,
        expected_sha256=expected_sha256, client_sha256=client_sha256,
        terminal_ordinal=terminal_ordinal)
    directory, basename = _open_parent(destination)
    try:
        writer = os.open(basename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=directory)
        try:
            created = os.fstat(writer)
            if not stat.S_ISREG(created.st_mode) or created.st_nlink != 1:
                raise ValueError('Authoritative caller-tail file must be regular')
            cursor = 0
            while cursor < len(payload):
                written = os.write(writer, memoryview(payload)[cursor:])
                if written <= 0:
                    raise OSError('Caller-tail write made no progress')
                cursor += written
            os.fsync(writer)
        finally:
            os.close(writer)
        os.fsync(directory)
        reader = os.open(basename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:
            opened = os.fstat(reader)
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or (opened.st_dev, opened.st_ino) !=
                    (created.st_dev, created.st_ino) or opened.st_size != len(payload)):
                raise ValueError('Independent caller-tail readback identity changed')
            digest = hashlib.sha256()
            count = 0
            while True:
                block = os.read(reader, min(65536, len(payload) + 1 - count))
                if not block:
                    break
                count += len(block)
                if count > len(payload):
                    raise ValueError('Independent caller-tail readback grew')
                digest.update(block)
            after = os.fstat(reader)
            if (after.st_nlink != 1 or count != len(payload) or digest.hexdigest() != expected_sha256
                    or (after.st_size, after.st_mtime_ns, after.st_ctime_ns) !=
                    (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)):
                raise ValueError('Independent caller-tail readback bytes changed')
        finally:
            os.close(reader)
        current = os.stat(basename, dir_fd=directory, follow_symlinks=False)
        if current.st_nlink != 1 or (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns, current.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('Authoritative caller-tail path changed after readback')
        return {'schema': READBACK_SCHEMA, 'destination': destination,
                'client_sha256': client_sha256,
                'stored_record_ordinals': [r['ordinal'] for r in value['records']],
                'payload_bytes': len(payload), 'payload_sha256': expected_sha256,
                'reopened_bytes': count, 'reopened_sha256': digest.hexdigest(),
                'durable': True, 'single_authoritative_file': True,
                'exact_readback_verified': True, 'directory_entry_fsynced': True,
                'independent_reopen': True, 'includes_terminal_delivery_acknowledgement': True,
                **AUTHORITY}
    finally:
        os.close(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True)
    parser.add_argument('--payload-base64', required=True)
    parser.add_argument('--expected-bytes', required=True, type=int)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--client-sha256', required=True)
    parser.add_argument('--terminal-ordinal', required=True, type=int)
    args = parser.parse_args()
    try:
        if len(args.payload_base64) > MAX_BASE64_BYTES:
            raise ValueError('Caller-tail base64 exceeds bounded shell argument component')
        payload = base64.b64decode(args.payload_base64, validate=True)
        if base64.b64encode(payload).decode() != args.payload_base64:
            raise ValueError('Canonical caller-tail base64 required')
        result = persist_tail(args.destination, payload, expected_bytes=args.expected_bytes,
            expected_sha256=args.expected_sha256, client_sha256=args.client_sha256,
            terminal_ordinal=args.terminal_ordinal)
        print(canonical(result).decode())
        return 0
    except Exception as error:
        print(canonical({'schema': READBACK_SCHEMA, 'status': 'CLOSED_FAILED',
                         'error': str(error), 'durable': False, **AUTHORITY}).decode())
        return 1


if __name__ == '__main__':
    sys.exit(main())
