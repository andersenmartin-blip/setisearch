"""Bounded lossless JSON-domain metadata + opaque assets; never pickle."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
from pathlib import Path
import os
import re
import struct

import msgpack


FORMAT = 'SETI_JSON_DOMAIN_KEYPOOL_MSGPACK_GZIP_BUNDLE_V2'
SAFE_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$')


class QuotaExceeded(ValueError):
    pass


def digest_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1 << 20):
            h.update(block)
    return h.hexdigest()


def validate(value, depth=0, active=None):
    """Accept an explicit JSON value domain without casts or nonfinite scalars."""
    if depth > 128:
        raise ValueError('Metadata nesting limit exceeded')
    t = type(value)
    if value is None or t in (bool, str):
        return
    if t is int:
        if not -(1 << 63) <= value < (1 << 64):
            raise ValueError('Integer outside declared MessagePack int64/uint64 domain')
        return
    if t is float:
        if not math.isfinite(value):
            raise ValueError('Nonfinite scalar: caller must preserve it in an explicit descriptor')
        return
    if t not in (dict, list):
        raise TypeError('Unsupported metadata type: ' + t.__name__)
    active = set() if active is None else active
    if id(value) in active:
        raise ValueError('Cyclic metadata')
    active.add(id(value))
    try:
        if t is dict:
            for key, child in value.items():
                if type(key) is not str:
                    raise TypeError('Metadata keys must be strings without coercion')
                validate(child, depth + 1, active)
        else:
            for child in value:
                validate(child, depth + 1, active)
    finally:
        active.remove(id(value))


def semantic_digest(value):
    """Type-tagged digest, preserving dict/list order and binary64 bits."""
    h = hashlib.sha256()

    def put(x):
        t = type(x)
        if x is None:
            h.update(b'N')
        elif t is bool:
            h.update(b'T' if x else b'F')
        elif t is int:
            b = str(x).encode('ascii'); h.update(b'I' + struct.pack('>I', len(b)) + b)
        elif t is float:
            h.update(b'D' + struct.pack('>d', x))
        elif t is str:
            b = x.encode('utf-8'); h.update(b'S' + struct.pack('>I', len(b)) + b)
        elif t is list:
            h.update(b'L' + struct.pack('>I', len(x)))
            for child in x: put(child)
        elif t is dict:
            h.update(b'M' + struct.pack('>I', len(x)))
            for key, child in x.items(): put(key); put(child)
        else:
            raise TypeError('Unsupported digest type')
    put(value)
    return h.hexdigest()


class Budget:
    def __init__(self, cap):
        if type(cap) is not int or cap <= 0:
            raise ValueError('Positive integer byte cap required')
        self.cap = cap
        self.used = 0

    def writer(self, path):
        return BudgetWriter(path, self)


class BudgetWriter:
    def __init__(self, path, budget):
        self.stream = Path(path).open('xb')
        self.budget = budget

    def write(self, block):
        if len(block) > self.budget.cap - self.budget.used:
            raise QuotaExceeded('Cumulative bundle byte cap exhausted; partial output retained')
        count = self.stream.write(block)
        self.budget.used += count
        return count

    def tell(self): return self.stream.tell()
    def flush(self): self.stream.flush()
    def __enter__(self): return self
    def __exit__(self, *args):
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.stream.close()


def safe_name(name):
    if type(name) is not str or SAFE_NAME.fullmatch(name) is None or name in ('.', '..'):
        raise ValueError('Unsafe bundle member name')
    return name


def key_pool(value):
    keys = {}
    def visit(x):
        if type(x) is dict:
            for key, child in x.items():
                if key not in keys:
                    if len(keys) >= 65535: raise ValueError('Too many distinct metadata keys')
                    keys[key] = len(keys)
                visit(child)
        elif type(x) is list:
            for child in x: visit(child)
    visit(value)
    return keys


def stream_pooled_metadata(value, keys, stream):
    """Preserve every value/order; only map KEY strings become pool references.

    Emit bounded chunks rather than constructing the entire packed object.
    No candidate/table filtering, float cast, score arithmetic or array decode.
    """
    packer = msgpack.Packer(use_bin_type=True, strict_types=True, use_single_float=False)
    buffer = bytearray()
    def emit(block):
        buffer.extend(block)
        if len(buffer) >= 65536:
            stream.write(buffer)
            buffer.clear()
    def put(x):
        if type(x) is dict:
            emit(packer.pack_map_header(len(x)))
            for key, child in x.items():
                emit(packer.pack(msgpack.ExtType(1, struct.pack('>H', keys[key]))))
                put(child)
        elif type(x) is list:
            emit(packer.pack_array_header(len(x)))
            for child in x: put(child)
        else:
            emit(packer.pack(x))
    put(value)
    if buffer: stream.write(buffer)


def write_bundle(folder, metadata, assets, cap):
    validate(metadata)
    if set(assets) & {'output.msgpack.gz', 'MANIFEST.json', 'KEYS.json'}:
        raise ValueError('Reserved bundle filename')
    for name in assets: safe_name(name)
    folder = Path(folder)
    folder.mkdir()  # Once-only; never overwrite an existing or partial bundle.
    budget = Budget(cap)
    metadata_sha = semantic_digest(metadata)
    keys = key_pool(metadata)
    with budget.writer(folder / 'KEYS.json') as stream:
        stream.write((json.dumps(list(keys), ensure_ascii=True) + '\n').encode())
    with budget.writer(folder / 'output.msgpack.gz') as stream:
        with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0, compresslevel=1) as zipped:
            stream_pooled_metadata(metadata, keys, zipped)
    for name, source in assets.items():
        with Path(source).open('rb') as inp, budget.writer(folder / name) as out:
            while block := inp.read(1 << 16):
                out.write(block)
    members = {p.name: {'bytes': p.stat().st_size, 'sha256': digest_file(p)}
               for p in sorted(folder.iterdir()) if p.is_file()}
    manifest = {'format': FORMAT, 'metadata': 'output.msgpack.gz',
                'semantic_sha256': metadata_sha, 'members': members, 'key_pool': 'KEYS.json',
                'msgpack_version': msgpack.__version__,
                'binary64_preserved': True, 'no_record_filter_or_float_rounding': True}
    raw = (json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with budget.writer(folder / 'MANIFEST.json') as stream: stream.write(raw)
    fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    return {'payload_bytes': budget.used, 'manifest_sha256': digest_file(folder / 'MANIFEST.json'),
            'semantic_sha256': metadata_sha, 'members': len(members)}


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            raise ValueError('Nonstring or duplicate map key')
        result[key] = value
    return result


def reject_extension(code, value):
    raise ValueError('MessagePack extensions are not admitted')


def verify_bundle(folder, *, cap, metadata_unpacked_cap=128 * 1024**2):
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError('Regular payload directory required')
    entries = list(folder.iterdir())
    if any(p.is_symlink() or not p.is_file() for p in entries):
        raise ValueError('Symlink, subdirectory or special file in payload')
    actual = {p.name: p for p in entries}
    if 'MANIFEST.json' not in actual or actual['MANIFEST.json'].stat().st_size > 1 << 20:
        raise ValueError('Missing or oversized manifest')
    total = sum(p.stat().st_size for p in entries)
    if total > cap:
        raise QuotaExceeded('Persisted payload exceeds declared byte cap')
    manifest = json.loads(actual['MANIFEST.json'].read_text(), object_pairs_hook=unique_pairs)
    if manifest.get('format') != FORMAT or manifest.get('metadata') != 'output.msgpack.gz':
        raise ValueError('Unsupported format')
    members = manifest['members']
    if not isinstance(members, dict) or len(members) > 128:
        raise ValueError('Invalid member inventory')
    for name in members: safe_name(name)
    if 'MANIFEST.json' in members or set(actual) != set(members) | {'MANIFEST.json'}:
        raise ValueError('Payload member inventory differs')
    for name, pin in members.items():
        if (type(pin['bytes']) is not int or pin['bytes'] < 0 or
                actual[name].stat().st_size != pin['bytes'] or
                digest_file(actual[name]) != pin['sha256']):
            raise ValueError('Member hash/length differs: ' + name)
    if manifest.get('key_pool') != 'KEYS.json' or actual['KEYS.json'].stat().st_size > 1 << 20:
        raise ValueError('Missing or oversized key pool')
    keys = json.loads(actual['KEYS.json'].read_text())
    if (type(keys) is not list or len(keys) > 65535 or
            any(type(k) is not str for k in keys) or len(set(keys)) != len(keys)):
        raise ValueError('Invalid key pool')
    def key_reference(code, data):
        if code != 1 or len(data) != 2: return reject_extension(code, data)
        index = struct.unpack('>H', data)[0]
        if index >= len(keys): raise ValueError('Key pool index outside inventory')
        return keys[index]
    with gzip.open(actual['output.msgpack.gz'], 'rb') as stream:
        raw = stream.read(metadata_unpacked_cap + 1)
    if len(raw) > metadata_unpacked_cap:
        raise QuotaExceeded('Decompressed metadata limit exhausted')
    metadata = msgpack.unpackb(raw, raw=False, strict_map_key=True,
                              object_pairs_hook=unique_pairs, ext_hook=key_reference)
    validate(metadata)
    decoded_sha = semantic_digest(metadata)
    if decoded_sha != manifest['semantic_sha256']:
        raise ValueError('Decoded metadata bits, values or order differ')
    return metadata, {'status': 'TRANSPORT_INTEGRITY_ONLY', 'payload_bytes': total,
        'metadata_unpacked_bytes': len(raw), 'semantic_sha256': decoded_sha,
        'manifest_sha256': digest_file(folder / 'MANIFEST.json'),
        'members': len(members), 'key_pool_entries': len(keys),
        'scientific_integrity_or_QA_established': False}
