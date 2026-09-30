#!/usr/bin/env python3
"""Local, bounded stdin/file adapter for the unchanged filesystem Store.

The first stdin line is a small canonical command. Only write_utf8 accepts a
following raw UTF-8 payload. This boundary is a local subprocess, never a tool
call or an execution/reservation verifier.
"""
import hashlib
import json
import os
import resource
import sys

from seti_repeater.empty_null_radio import canonical
from seti_repeater.native_v2_bridge_radio import (
    CHUNK_BYTES, MIB, Store, _dispatch, _directory, _integer, _json_small,
    _regular, _sha, git_projection,
)

HEADER_BYTES = MIB
PROJECTION_SCHEMA = 'radio-native-v2-local-projection-verification-v1'


def _source(store, receipt, kind='git_projection'):
    expected = {'id', 'path', 'bytes', 'sha256', 'durable'}
    if not isinstance(receipt, dict) or set(receipt) != expected or receipt['durable'] is not True:
        raise ValueError('Exact durable local projection receipt required')
    _integer(receipt['bytes'], 64*MIB, 'source bytes'); _sha(receipt['sha256'])
    if receipt['path'] != store.root+'/items/'+receipt['id']+'/part':
        raise ValueError('Source must be the sole sealed part in this Store')
    with store._locked() as (_, items, manifest):
        item = store._item(items, receipt['id'])
        try:
            intent = _json_small(item, 'intent.json')
            marker = _json_small(item, 'sealed.json')
            if intent['kind'] != kind or marker['bytes'] != receipt['bytes'] or marker['sha256'] != receipt['sha256']:
                raise ValueError('Exact sealed Git projection source required')
            fd = os.open('part', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=item)
            if _regular(fd).st_size != receipt['bytes']:
                os.close(fd)
                raise ValueError('Sealed source size differs')
            return fd
        finally:
            os.close(item)


def _fill(store, identity, stream, size, digest, *, last=True):
    _integer(size, 64*MIB, 'payload bytes'); _sha(digest)
    actual = hashlib.sha256(); offset = 0
    while offset < size:
        raw = stream.read(min(CHUNK_BYTES, size-offset))
        if not raw:
            raise ValueError('Truncated local immutable payload')
        actual.update(raw); store.append(identity, offset, raw); offset += len(raw)
    if (last and stream.read(1)) or actual.hexdigest() != digest:
        raise ValueError('Exact local payload length/SHA256 differs')
    return store.seal(identity, size=size, sha256=digest)


def _request_view_receipt(store, command):
    """Escape one pinned Worker params range directly into its raw receipt."""
    view = command['view']; expected = command['expected']
    if (view.get('schema') != 'radio-native-v2-existing-request-view-v1'
            or view['request_bytes'] != expected['request_bytes']
            or view['request_sha256'] != expected['request_sha256']):
        raise ValueError('Exact bounded immutable request view required')
    _integer(expected['response_bytes'], 4*MIB, 'raw connector response')
    response = sys.stdin.buffer.read(expected['response_bytes']+1)
    if len(response) != expected['response_bytes'] or hashlib.sha256(response).hexdigest() != expected['response_sha256']:
        raise ValueError('Untouched raw connector response bytes/SHA256 differ')
    source = {'id': view['path'].split('/')[-2], 'path': view['path'],
              'bytes': view['source_bytes'], 'sha256': view['source_sha256'], 'durable': True}
    fd = _source(store, source, 'request')
    try:
        full = hashlib.sha256()
        while raw := os.read(fd, CHUNK_BYTES):
            full.update(raw)
        if full.hexdigest() != view['source_sha256']:
            raise ValueError('Immutable whole Worker request source differs')
        _integer(view['offset'], source['bytes'], 'view offset')
        _integer(view['bytes'], source['bytes']-view['offset'], 'view bytes')
        store.reserve(command['id'], 'host_receipt', expected['stored_bytes'], expected['stored_sha256'], command['case_ordinal'])
        buffered = bytearray(); offset = 0; stored = hashlib.sha256(); request = hashlib.sha256(); params = hashlib.sha256()
        def emit(raw):
            nonlocal offset
            stored.update(raw); buffered.extend(raw)
            while len(buffered) >= CHUNK_BYTES:
                store.append(command['id'], offset, bytes(buffered[:CHUNK_BYTES])); offset += CHUNK_BYTES
                del buffered[:CHUNK_BYTES]
        def escape(raw):
            return json.dumps(raw.decode('utf-8'), ensure_ascii=False, separators=(',', ':'))[1:-1].encode('utf-8')
        prefix = view['request_prefix'].encode('ascii'); suffix = view['request_suffix'].encode('ascii')
        emit(b'{"request_json":"'); emit(escape(prefix)); request.update(prefix)
        os.lseek(fd, view['offset'], os.SEEK_SET); remaining = view['bytes']
        while remaining:
            raw = os.read(fd, min(CHUNK_BYTES, remaining))
            if not raw or any(byte > 127 for byte in raw):
                raise ValueError('Exact ASCII immutable params range required')
            request.update(raw); params.update(raw); emit(escape(raw)); remaining -= len(raw)
        request.update(suffix); emit(escape(suffix)); emit(b'","response_json":"'); emit(escape(response)); emit(b'"}')
        if (params.hexdigest() != view['sha256'] or request.hexdigest() != expected['request_sha256']
                or len(prefix)+view['bytes']+len(suffix) != expected['request_bytes']):
            raise ValueError('Exact actual request bytes/SHA256 differ')
        if buffered:
            store.append(command['id'], offset, bytes(buffered)); offset += len(buffered)
        if offset != expected['stored_bytes'] or stored.hexdigest() != expected['stored_sha256']:
            raise ValueError('Exact streaming raw request/reply receipt differs')
        return store.seal(command['id'], size=offset, sha256=stored.hexdigest())
    finally:
        os.close(fd)


def main():
    header = sys.stdin.buffer.readline(HEADER_BYTES+1)
    if not header.endswith(b'\n') or len(header) > HEADER_BYTES:
        raise ValueError('Bounded canonical local helper header required')
    command = json.loads(header)
    if canonical(command)+b'\n' != header or not isinstance(command, dict):
        raise ValueError('Exact canonical local helper command required')
    store = Store(command['root'])
    action = command['action']
    try:
        if action == 'write_request_view_receipt':
            result = _request_view_receipt(store, command)
        elif action == 'write_frames':
            frames = command['frames']
            if not isinstance(frames, list) or not 1 <= len(frames) <= 128:
                raise ValueError('Bounded local receipt frame inventory required')
            if sum(frame['bytes'] for frame in frames) > 64*MIB:
                raise ValueError('Total local framed stdin payload exceeds bound')
            for frame in frames:
                if set(frame) != {'id', 'kind', 'bytes', 'sha256', 'case_ordinal'} or frame['kind'] != 'host_receipt':
                    raise ValueError('Exact host receipt frame metadata required')
                store.reserve(frame['id'], frame['kind'], frame['bytes'], frame['sha256'], frame['case_ordinal'])
            result = []
            for index, frame in enumerate(frames):
                result.append(_fill(store, frame['id'], sys.stdin.buffer, frame['bytes'],
                                    frame['sha256'], last=index == len(frames)-1))
        elif action in ('write_utf8', 'fill_utf8'):
            if action == 'write_utf8':
                store.reserve(command['id'], command['kind'], command['bytes'],
                              command['sha256'], command.get('case_ordinal'))
            else:
                with store._locked() as (_, items, manifest):
                    item = store._item(items, command['id'])
                    try:
                        intent = _json_small(item, 'intent.json')
                        if intent['kind'] != 'response' or command['bytes'] > intent['reserved_bytes']:
                            raise ValueError('Pre-reserved response required for raw fill')
                    finally:
                        os.close(item)
            result = _fill(store, command['id'], sys.stdin.buffer,
                           command['bytes'], command['sha256'])
        elif action == 'ingest_pinned_file':
            if sys.stdin.buffer.read(1):
                raise ValueError('File ingestion accepts a small header only')
            source = command['source']; fd = _source(store, source)
            with os.fdopen(fd, 'rb') as stream:
                result = _fill(store, command['id'], stream, source['bytes'], source['sha256'])
        elif action == 'git_projection':
            if sys.stdin.buffer.read(1):
                raise ValueError('Projection accepts a small header only')
            result = git_projection(store, command['id'], command['spool_path'],
                                    command['commit'], command['paths'], command['files'],
                                    command.get('case_ordinal'))
            result['projection_verification'] = {
                'schema': PROJECTION_SCHEMA, 'commit': command['commit'],
                'paths_sha256': hashlib.sha256(canonical(command['paths'])).hexdigest(),
                'file_pins_sha256': hashlib.sha256(canonical(command['files'])).hexdigest(),
                'raw_git_sha256': result['raw_git_receipt']['sha256'],
                'projection_sha256': result['projection']['sha256'],
                'exact_frozen_blob_sha256': True, 'exact_git_blob_identity': True,
                'exact_batch_framing': True,
            }
        elif action == 'stop':
            store.stop(command['reason']); result = {'stopped': True, 'automatic_retry': False}
        else:
            if sys.stdin.buffer.read(1):
                raise ValueError('Metadata helper accepts a small header only')
            result = _dispatch(command)
        sys.stdout.buffer.write(canonical({'result': result, 'source_loader_preflight':
            getattr(sys, '_radio_native_v2_source_policy_preflight', None), 'local_process': {
            'pid': os.getpid(),
            'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        }})+b'\n')
    except BaseException as error:
        if action != 'create':
            store.stop(error)
        raise


if __name__ == '__main__':
    main()
