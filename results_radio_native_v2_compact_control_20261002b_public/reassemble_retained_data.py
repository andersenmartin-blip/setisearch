#!/usr/bin/env python3
"""Verify or copy retained failed-control bytes; grants no execution authority."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

PUBLIC_DIRECTORY = 'results_radio_native_v2_compact_control_20261002b_public'
ACTUAL_DIRECTORY = 'results_radio_native_v2_compact_control_20261002b'
MANIFEST_SHA256 = '8f88e15caaffbb8f8ec55d37e13264e716ca09ec73a3760bfb036a00a2138e37'
CHUNK_BYTES = 2097152
FILES = {
    ACTUAL_DIRECTORY + '/cases/case00/deterministic-source.bin':
        ('deterministic-source', 'deterministic-source.bin'),
    ACTUAL_DIRECTORY + '/cases/case00/store/items/request-000001/part':
        ('request-part', 'request-part.bin'),
}


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate manifest key refused')
        result[key] = value
    return result


def read_regular(repo, relative, maximum):
    parts = relative.split('/')
    if any(part in ('', '.', '..') for part in parts):
        raise ValueError('Canonical relative retained path required')
    path = repo
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('Retained path symlink refused')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise ValueError('Bounded regular retained file required')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(maximum + 1)
        after = os.fstat(fd)
        identity = lambda i: (i.st_dev, i.st_ino, i.st_mode, i.st_size,
                              i.st_nlink, i.st_mtime_ns, i.st_ctime_ns)
        if len(raw) != before.st_size or identity(before) != identity(after):
            raise ValueError('Retained file changed during read')
        return raw
    finally:
        os.close(fd)


def load_manifest(repo):
    raw = read_regular(repo, PUBLIC_DIRECTORY + '/chunk-manifest.json', 65536)
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError('Retained manifest differs from the pinned byte hash')
    manifest = json.loads(raw, object_pairs_hook=unique_pairs)
    if (manifest['schema'] != 'radio-native-v2-failed-control-byte-exact-chunk-retention-v1'
            or manifest['status'] != 'CLOSED_FAILED_DATA_RETENTION_ONLY'
            or manifest['chunk_bytes_maximum'] != CHUNK_BYTES
            or len(manifest['files']) != len(FILES)
            or {row['original_path'] for row in manifest['files']} != set(FILES)):
        raise ValueError('Exact failed-control retention manifest required')
    return manifest


def process_chunks(repo, manifest, output=None):
    results = []
    for row in manifest['files']:
        prefix, name = FILES[row['original_path']]
        size = row['original_bytes']
        if type(size) is not int or not 0 < size <= 128 * 1024 * 1024:
            raise ValueError('Bounded positive original size required')
        if not 0 < len(row['chunks']) <= 64:
            raise ValueError('Bounded ordered chunk list required')
        digest = hashlib.sha256()
        git_digest = hashlib.sha1(b'blob ' + str(size).encode() + b'\0')
        count = 0
        fd = None
        try:
            if output is not None:
                fd = os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            for index, chunk in enumerate(row['chunks']):
                expected = PUBLIC_DIRECTORY + '/' + prefix + '/part%03d.bin' % index
                length = chunk['bytes']
                if (chunk['path'] != expected or type(chunk['offset']) is not int
                        or chunk['offset'] != count or type(length) is not int
                        or not 0 < length <= CHUNK_BYTES
                        or not re.fullmatch('[0-9a-f]{64}', chunk['sha256'])
                        or not re.fullmatch('[0-9a-f]{40}', chunk['git_blob_sha'])):
                    raise ValueError('Exact contiguous chunk mapping required')
                raw = read_regular(repo, expected, CHUNK_BYTES)
                if (len(raw) != length or hashlib.sha256(raw).hexdigest() != chunk['sha256']
                        or hashlib.sha1(b'blob ' + str(length).encode() + b'\0' + raw).hexdigest()
                        != chunk['git_blob_sha']):
                    raise ValueError('Retained chunk size or hash differs')
                digest.update(raw)
                git_digest.update(raw)
                count += length
                if fd is not None:
                    pending = memoryview(raw)
                    while pending:
                        written = os.write(fd, pending)
                        if written <= 0:
                            raise OSError('Retained copy write made no progress')
                        pending = pending[written:]
            if (count != size or digest.hexdigest() != row['original_sha256']
                    or git_digest.hexdigest() != row['original_git_blob_sha']):
                raise ValueError('Retained whole-file size or hash differs')
            if fd is not None:
                os.fsync(fd)
        finally:
            if fd is not None:
                os.close(fd)
        results.append({'name': name, 'bytes': count, 'sha256': digest.hexdigest(),
                        'git_blob_sha': git_digest.hexdigest(), 'chunks': len(row['chunks'])})
    return results


def fresh_output_path(repo, value):
    requested = Path(value).absolute()
    output = requested.parent.resolve(strict=True) / requested.name
    for protected in (repo / ACTUAL_DIRECTORY, repo / '.radio-native-v2-invocation-ledger',
                      repo / PUBLIC_DIRECTORY):
        for root in (protected, protected.resolve(strict=False)):
            if output == root or root in output.parents:
                raise ValueError('Actual scope, ledger and retention input destinations refused')
    if os.path.lexists(output):
        raise FileExistsError('A fresh nonexistent output directory is required')
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group()
    options.add_argument('--verify-only', action='store_true', help='Hash without writing (default)')
    options.add_argument('--output-dir', help='Create a fresh directory for byte-identical retained copies')
    args = parser.parse_args(argv)
    repo = Path(__file__).resolve().parent.parent
    output = fresh_output_path(repo, args.output_dir) if args.output_dir is not None else None
    manifest = load_manifest(repo)
    results = process_chunks(repo, manifest)
    if output is not None:
        # mkdir fails if another actor created the requested directory meanwhile.
        os.mkdir(output, 0o700)
        copied = process_chunks(repo, manifest, output)
        if copied != results:
            raise ValueError('Retained bytes changed between verification and copying')
        directory = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    print(json.dumps({'status': 'CLOSED_FAILED_DATA_RETENTION_ONLY',
        'mode': 'verified_only' if output is None else 'retained_bytes_copied',
        'manifest_sha256': MANIFEST_SHA256, 'files': results,
        'output_dir': str(output) if output is not None else None,
        'new_control_invocations': 0, 'new_source_generation': False,
        'scientific_execution_authorized': False, 'native_execution_authorized': False,
        'automatic_retry': False}, sort_keys=True, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
