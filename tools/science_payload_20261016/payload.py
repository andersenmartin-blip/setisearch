"""Lossless nested scientific values over pinned, bounded transport primitives.

This module transports supplied values; it never generates, admits, searches,
normalizes, ranks, or scientifically approves a case. Arrays are written and
checked individually. Opening an archive authenticates every array body without
loading the collection. ``load(path)`` materializes only that selected field.

Supported values are exact Python dict/list/tuple/None/bool/str/int/float,
NumPy ndarrays and NumPy scalars with non-object, metadata-free dtypes. Dict
keys are immutable scalar/tuple values. Array bytes are the original logical C-order bytes; views and
Fortran layouts retain their dtype, shape and values, not their Python strides.
Container alias identity is not a part of the transport contract.
"""
from __future__ import annotations

import ast
from collections.abc import Mapping
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import sys
import zipfile

import numpy as np


SCHEMA = 'SETI_LOSSLESS_SCIENCE_VALUE_BUNDLE_V1'
TAG = '__seti_lossless_typed_value_v1__'
ARRAY_FILE = 'science_arrays.npz'
DEPENDENCIES = {
    'bounded_payload_20261015/payload_store.py':
        '494283c37cc0fdc68c78531cbaf4b352db6aa302ee13af2d4f6e89c8fd3d1144',
    'fullcase_payload_20261015/array_adapter.py':
        'c531ff63f4712e05bd5e49aa4771d3b65e33ae85aa3b0a9147d3181c0c4d4a75',
}
SEMANTICS = {'array_order': 'logical_C', 'container_alias_identity': False,
             'scientific_integrity_or_QA_or_admission_established': False}


def _pinned_module(name, relative):
    path = Path(__file__).resolve().parent.parent / relative
    if hashlib.sha256(path.read_bytes()).hexdigest() != DEPENDENCIES[relative]:
        raise ValueError('Pinned transport dependency differs: ' + relative)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


store = _pinned_module('science_payload_pinned_store', 'bounded_payload_20261015/payload_store.py')
arrays = _pinned_module('science_payload_pinned_arrays', 'fullcase_payload_20261015/array_adapter.py')
QuotaExceeded = store.QuotaExceeded


def _dtype_spec(dtype):
    if dtype.hasobject or dtype.metadata is not None:
        raise TypeError('Object-containing or metadata-bearing NumPy dtype is unsupported')
    if dtype.subdtype is not None:
        base, shape = dtype.subdtype
        return (_dtype_spec(base), shape)
    if dtype.fields is not None:
        fields = [dtype.fields[name] for name in dtype.names]
        return {'names': list(dtype.names), 'formats': [_dtype_spec(f[0]) for f in fields],
                'offsets': [f[1] for f in fields], 'itemsize': dtype.itemsize,
                'titles': [f[2] if len(f) > 2 else None for f in fields],
                'aligned': bool(dtype.isalignedstruct)}
    return dtype.str


def _dtype_record(dtype):
    # dtype.str alone collapses structured fields into an opaque void dtype.
    return {'dtype': dtype.str,
            'dtype_descr_repr': repr(_dtype_spec(dtype)),
            'dtype_isalignedstruct': bool(dtype.isalignedstruct)}


def _record_dtype(record):
    text = record['dtype_descr_repr']
    if type(text) is not str or len(text) > 4096:
        raise ValueError('Invalid or oversized dtype descriptor')
    dtype = np.dtype(ast.literal_eval(text), align=record['dtype_isalignedstruct'])
    if _dtype_record(dtype) != {k: record[k] for k in _dtype_record(dtype)}:
        raise ValueError('Noncanonical dtype descriptor')
    return dtype


def _c_array(value):
    if value.flags.c_contiguous:
        return value
    if value.dtype.fields is not None:
        return np.ndarray(value.shape, dtype=value.dtype, buffer=value.tobytes(order='C'), order='C')
    return np.array(value, order='C', copy=True, subok=False)


def _encode_key(value, depth=0):
    if depth > 100:
        raise ValueError('Map key nesting limit exceeded')
    if value is None or type(value) in (bool, str):
        return value
    if type(value) is int:
        return value if -(1 << 63) <= value < (1 << 64) else {TAG: ['integer', str(value)]}
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is tuple:
        return {TAG: ['tuple', [_encode_key(child, depth + 1) for child in value]]}
    raise TypeError('Map keys must be finite immutable Python scalars or tuples')


def _decode_key(value):
    tag = _tag(value)
    if tag and tag[0] == 'tuple':
        return tuple(_decode_key(child) for child in tag[1])
    if tag and tag[0] == 'integer':
        return int(tag[1])
    if tag:
        raise ValueError('Invalid typed map key')
    if value is None or type(value) in (bool, str, int) or type(value) is float and math.isfinite(value):
        return value
    raise ValueError('Invalid map key')


def _path_metadata(path):
    return [_encode_key(component) for component in path]


def _encode(value, refs, specs, path=(), active=None, depth=0):
    if depth > 100:
        raise ValueError('Scientific value nesting limit exceeded')
    t = type(value)
    if value is None or t in (bool, str):
        return value
    if t is int:
        return value if -(1 << 63) <= value < (1 << 64) else {TAG: ['integer', str(value)]}
    if t is float:
        return value if math.isfinite(value) else {TAG: ['binary64', struct.pack('>d', value).hex()]}
    if t is np.ndarray or isinstance(value, np.generic):
        scalar = t is not np.ndarray
        array = np.asarray(value) if scalar else value
        dtype = _dtype_record(array.dtype)
        key = 'array_' + str(len(specs)).zfill(6)
        specs.append({'key': key, 'path': _path_metadata(path), 'shape': list(array.shape),
                      'nbytes': array.nbytes, **dtype})
        refs.append(array)
        return {TAG: ['numpy_scalar' if scalar else 'array', key]}
    if t not in (dict, list, tuple):
        raise TypeError('Unsupported scientific value type: ' + t.__name__)
    active = set() if active is None else active
    if id(value) in active:
        raise ValueError('Cyclic scientific value')
    active.add(id(value))
    try:
        if t is dict:
            encoded_items = [[_encode_key(key), _encode(child, refs, specs, path + (key,), active, depth + 1)]
                             for key, child in value.items()]
            if TAG in value or any(type(key) is not str for key in value):
                return {TAG: ['dict', encoded_items]}
            return {key: child for key, child in encoded_items}
        children = [_encode(child, refs, specs, path + (i,), active, depth + 1)
                    for i, child in enumerate(value)]
        return {TAG: ['tuple', children]} if t is tuple else children
    finally:
        active.remove(id(value))


def _inventory(folder):
    return {p.name: {'bytes': p.stat().st_size, 'sha256': store.digest_file(p)}
            for p in sorted(Path(folder).iterdir()) if p.is_file()}


def write_payload(folder, payload, *, cap, array_physical_cap=None):
    """Persist one new, once-only bundle. Failure retains bounded partial output.

    ``cap`` bounds the sum of all physical files including the final manifest.
    The optional smaller ``array_physical_cap`` bounds just the NPZ writer.
    No input container or array is modified. No existing path is overwritten.
    """
    budget = store.Budget(cap)
    if array_physical_cap is None:
        array_physical_cap = cap
    if type(array_physical_cap) is not int or not 0 < array_physical_cap <= cap:
        raise ValueError('Array physical cap must be a positive integer within total cap')
    references, specs = [], []
    tree = _encode(payload, references, specs)
    folder = Path(folder)
    folder.mkdir()
    by_key = {spec['key']: value for spec, value in zip(specs, references)}
    descriptors = arrays.write_arrays(folder / ARRAY_FILE, specs,
        lambda spec: _c_array(by_key[spec['key']]), budget, physical_cap=array_physical_cap)
    document = {'schema': SCHEMA, 'tree': tree, 'arrays': descriptors,
                'dependencies': DEPENDENCIES, 'semantics': SEMANTICS}
    store.validate(document)
    keys = store.key_pool(document)
    with budget.writer(folder / 'KEYS.json') as stream:
        stream.write((json.dumps(list(keys), ensure_ascii=True) + '\n').encode())
    with budget.writer(folder / 'output.msgpack.gz') as stream:
        with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0, compresslevel=1) as zipped:
            store.stream_pooled_metadata(document, keys, zipped)
    digest = store.semantic_digest(document)
    manifest = {'format': store.FORMAT, 'metadata': 'output.msgpack.gz',
                'semantic_sha256': digest, 'members': _inventory(folder), 'key_pool': 'KEYS.json',
                'msgpack_version': store.msgpack.__version__, 'binary64_preserved': True,
                'no_record_filter_or_float_rounding': True}
    with budget.writer(folder / 'MANIFEST.json') as stream:
        stream.write((json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + '\n').encode())
    fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return {'status': 'LOSSLESS_SCIENTIFIC_VALUE_TRANSPORT_ONLY',
            'payload_bytes': budget.used, 'semantic_sha256': digest,
            'manifest_sha256': store.digest_file(folder / 'MANIFEST.json'),
            'arrays_written': len(descriptors), 'all_array_raw_bytes': sum(s['nbytes'] for s in specs),
            'inventory': _inventory(folder),
            'scientific_integrity_or_QA_or_admission_established': False}


def _tag(node):
    if type(node) is dict and set(node) == {TAG}:
        value = node[TAG]
        if type(value) is not list or len(value) != 2 or type(value[0]) is not str:
            raise ValueError('Malformed scientific value tag')
        return value
    return None


def _children(node):
    tag = _tag(node)
    if tag and tag[0] == 'dict':
        pairs = tag[1]
        if (type(pairs) is not list or any(type(p) is not list or len(p) != 2 or
                _encode_key(_decode_key(p[0])) != p[0] for p in pairs)):
            raise ValueError('Malformed escaped dict')
        result = {_decode_key(key): child for key, child in pairs}
        if len(result) != len(pairs):
            raise ValueError('Duplicate escaped map key')
        return result
    if tag and tag[0] == 'tuple':
        if type(tag[1]) is not list:
            raise ValueError('Malformed tuple')
        return tag[1]
    return node


class _ArrayLookup(Mapping):
    def __init__(self, archive):
        self.archive = archive
    def __getitem__(self, key):
        descriptor = self.archive.by_key[key]
        dtype = _record_dtype(descriptor)
        if dtype.fields is None:
            value = arrays.load_typed_array(self.archive.folder / ARRAY_FILE, descriptor)
        else:
            # NumPy's non-file NPY reader assigns structured records by fields,
            # which can discard original padding bytes. Read their raw buffer
            # explicitly; the pinned verifier has checked every original byte.
            with zipfile.ZipFile(self.archive.folder / ARRAY_FILE) as archive:
                with archive.open(key + '.npy') as stream:
                    if np.lib.format.read_magic(stream) != (1, 0):
                        raise ValueError('Unexpected NPY version')
                    shape, fortran, saved_dtype = np.lib.format.read_array_header_1_0(stream, max_header_size=4096)
                    if list(shape) != descriptor['shape'] or fortran or saved_dtype != dtype:
                        raise ValueError('Structured array header differs')
                    body = bytearray(descriptor['nbytes'])
                    view = memoryview(body)
                    count = 0
                    while count < len(body):
                        n = stream.readinto(view[count:count + (1 << 20)])
                        if not n:
                            raise ValueError('Truncated structured array body')
                        count += n
                    if stream.read(1) or hashlib.sha256(body).hexdigest() != descriptor['C_order_input_sha256']:
                        raise ValueError('Structured array complete byte hash differs')
            value = np.ndarray(descriptor['shape'], dtype=dtype, buffer=body, order='C')
        if value.dtype != dtype:
            raise ValueError('Consumer array full dtype differs')
        if value.dtype.isalignedstruct != dtype.isalignedstruct:
            value = value.view(dtype)
        return value
    def __iter__(self):
        return iter(self.archive.by_key)
    def __len__(self):
        return len(self.archive.by_key)


class PayloadArchive:
    """Verified metadata plus a lazy, verified array accessor."""
    def __init__(self, folder, document, receipt):
        self.folder, self.tree, self.receipt = Path(folder), document['tree'], receipt
        self.descriptors = document['arrays']
        self.by_key = {d['key']: d for d in self.descriptors}
        self.array_store = _ArrayLookup(self)

    def _select(self, path):
        if type(path) not in (tuple, list):
            raise TypeError('Field path must be a tuple/list of original keys or indices')
        node = self.tree
        for component in path:
            tag = _tag(node)
            if tag and tag[0] not in ('tuple', 'dict'):
                raise KeyError('Cannot select through a scalar or numeric array')
            node = _children(node)
            if type(node) is dict:
                node = node[component]
            elif type(node) is list and type(component) is int and component >= 0:
                node = node[component]
            else:
                raise KeyError('Path component does not match original container')
        return node

    def _decode(self, node, qa=False):
        tag = _tag(node)
        if tag:
            kind, value = tag
            if kind in ('array', 'numpy_scalar'):
                descriptor = self.by_key[value]
                if qa and kind == 'array':
                    return {'array_descriptor': {'npz_key': value, 'shape': descriptor['shape'],
                        'dtype': str(_record_dtype(descriptor)),
                        'C_order_bytes_sha256': descriptor['C_order_input_sha256']}}
                result = self.array_store[value]
                return result[()] if kind == 'numpy_scalar' else result
            if kind == 'tuple':
                return tuple(self._decode(child, qa) for child in value)
            if kind == 'dict':
                return {_decode_key(key): self._decode(child, qa) for key, child in value}
            if kind == 'binary64':
                return struct.unpack('>d', bytes.fromhex(value))[0]
            if kind == 'integer':
                return int(value)
            raise ValueError('Unknown scientific value tag')
        if type(node) is dict:
            return {key: self._decode(child, qa) for key, child in node.items()}
        if type(node) is list:
            return [self._decode(child, qa) for child in node]
        return node

    def load(self, path=()):
        return self._decode(self._select(path))

    def materialize(self):
        """Explicit full reconstruction; ordinary field access does not call this."""
        return self.load(())

    def qa_decode_pair(self, path=('output',)):
        """Return legacy ``qa.decode(value, store, audit)`` inputs.

        Numeric arrays are descriptors; normalization and all other original
        lists retain their Python list type. The array store loads one field
        per request. A legacy decoder may only traverse dicts/lists; tuple
        preservation is guaranteed by ``load`` and should be tested separately.
        """
        return self._decode(self._select(path), qa=True), self.array_store


def _validate_tree(node, descriptors, path=(), seen=None, depth=0):
    if depth > 100:
        raise ValueError('Scientific value nesting limit exceeded')
    seen = [] if seen is None else seen
    tag = _tag(node)
    if tag:
        kind, value = tag
        if kind in ('array', 'numpy_scalar'):
            if type(value) is not str or value not in descriptors:
                raise ValueError('Unknown array reference')
            descriptor = descriptors[value]
            if descriptor['path'] != _path_metadata(path):
                raise ValueError('Array path differs from source container path')
            if kind == 'numpy_scalar' and descriptor['shape'] != []:
                raise ValueError('NumPy scalar must have zero-dimensional array storage')
            seen.append(value)
        elif kind in ('tuple', 'dict'):
            child = _children(node)
            iterable = child.items() if kind == 'dict' else enumerate(child)
            for key, value in iterable:
                _validate_tree(value, descriptors, path + (key,), seen, depth + 1)
        elif kind == 'binary64':
            if (type(value) is not str or len(value) != 16 or
                    math.isfinite(struct.unpack('>d', bytes.fromhex(value))[0])):
                raise ValueError('Invalid nonfinite binary64 descriptor')
        elif kind == 'integer':
            if type(value) is not str or str(int(value)) != value or -(1 << 63) <= int(value) < (1 << 64):
                raise ValueError('Invalid extended integer descriptor')
        else:
            raise ValueError('Unknown scientific value tag')
    elif type(node) is dict:
        if TAG in node:
            raise ValueError('Unescaped reserved sentinel')
        for key, value in node.items():
            _validate_tree(value, descriptors, path + (key,), seen, depth + 1)
    elif type(node) is list:
        for i, value in enumerate(node):
            _validate_tree(value, descriptors, path + (i,), seen, depth + 1)
    return seen


def verify_payload(folder, *, cap, expected_semantic_sha256=None,
                   metadata_unpacked_cap=128 * 1024**2, max_total_raw_bytes=512 * 1024**2):
    """Authenticate inventory, typed metadata, NPY headers and every raw byte.

    This establishes transport integrity only. An independent scientific QA
    remains necessary. Caller-supplied expected semantic digest pins the exact
    producer result rather than merely the bundle's internal consistency.
    """
    if type(cap) is not int or cap <= 0 or type(max_total_raw_bytes) is not int or max_total_raw_bytes < 0:
        raise ValueError('Positive physical cap and nonnegative raw-byte cap required')
    document, receipt = store.verify_bundle(folder, cap=cap, metadata_unpacked_cap=metadata_unpacked_cap)
    if (type(document) is not dict or set(document) != {'schema', 'tree', 'arrays', 'dependencies', 'semantics'}
            or document['schema'] != SCHEMA or document['dependencies'] != DEPENDENCIES
            or document['semantics'] != SEMANTICS):
        raise ValueError('Scientific payload schema or dependency pins differ')
    if expected_semantic_sha256 is not None and receipt['semantic_sha256'] != expected_semantic_sha256:
        raise ValueError('Expected producer semantic digest differs')
    if {p.name for p in Path(folder).iterdir()} != {ARRAY_FILE, 'output.msgpack.gz', 'KEYS.json', 'MANIFEST.json'}:
        raise ValueError('Scientific payload physical inventory differs')
    descriptors = document['arrays']
    if type(descriptors) is not list:
        raise ValueError('Array descriptor list required')
    expected_specs, raw_bytes = [], 0
    fields = {'key', 'path', 'shape', 'nbytes', 'dtype', 'dtype_descr_repr', 'dtype_isalignedstruct',
              'C_order_input_sha256', 'NPY_uncompressed_bytes'}
    for i, descriptor in enumerate(descriptors):
        if type(descriptor) is not dict or set(descriptor) != fields:
            raise ValueError('Array descriptor field inventory differs')
        if descriptor['key'] != 'array_' + str(i).zfill(6):
            raise ValueError('Array key census/order differs')
        if (type(descriptor['path']) is not list or any(_encode_key(_decode_key(p)) != p for p in descriptor['path'])
                or type(descriptor['shape']) is not list or len(descriptor['shape']) > 32
                or any(type(n) is not int or n < 0 for n in descriptor['shape'])
                or type(descriptor['dtype_isalignedstruct']) is not bool):
            raise ValueError('Invalid array path/shape/dtype descriptor')
        dtype = _record_dtype(descriptor)
        expected = math.prod(descriptor['shape']) * dtype.itemsize
        if type(descriptor['nbytes']) is not int or descriptor['nbytes'] != expected:
            raise ValueError('Array byte count differs from dtype and shape')
        raw_bytes += expected
        if raw_bytes > max_total_raw_bytes:
            raise QuotaExceeded('Declared decompressed array-byte limit exhausted')
        if (type(descriptor['NPY_uncompressed_bytes']) is not int or
                type(descriptor['C_order_input_sha256']) is not str or
                len(descriptor['C_order_input_sha256']) != 64):
            raise ValueError('Invalid NPY body integrity descriptor')
        expected_specs.append({k: v for k, v in descriptor.items()
                               if k not in ('C_order_input_sha256', 'NPY_uncompressed_bytes')})
    by_key = {d['key']: d for d in descriptors}
    if _validate_tree(document['tree'], by_key) != list(by_key):
        raise ValueError('Array references differ in census, order, or ownership')
    numeric = arrays.verify_arrays(Path(folder) / ARRAY_FILE, descriptors, expected_specs)
    # The older pinned adapter checks dtype.str. Also authenticate structured
    # field names, offsets and subarray descriptions without loading bodies.
    with zipfile.ZipFile(Path(folder) / ARRAY_FILE) as archive:
        for descriptor in descriptors:
            with archive.open(descriptor['key'] + '.npy') as stream:
                if np.lib.format.read_magic(stream) != (1, 0):
                    raise ValueError('Unexpected NPY version')
                _, _, dtype = np.lib.format.read_array_header_1_0(stream, max_header_size=4096)
                if dtype != _record_dtype(descriptor):
                    raise ValueError('NPY structured dtype differs')
    receipt.update(status='LOSSLESS_SCIENTIFIC_VALUE_TRANSPORT_ONLY', numeric=numeric,
                   inventory=_inventory(folder), all_array_raw_bytes=raw_bytes,
                   scientific_integrity_or_QA_or_admission_established=False)
    return PayloadArchive(folder, document, receipt)
