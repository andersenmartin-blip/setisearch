"""Explicitly pinned immutable direct-score handoff; synthetic engineering only.

Legacy numerical producers/consumers remain unchanged. A caller-held receipt
pin anchors reconstruction; a file or a newly calculated self-hash cannot do so.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
from types import MappingProxyType

import numpy as np
from . import pipeline_direct_radio as pipeline
from . import search_v0p6 as core
from . import transfer_m43g as native
from .detector_m43u import checked_vectors

SCHEMA = 'radio-sealed-direct-score-store-v1'
MAGIC = b'SETISCORE\x00\x01\x00'
PREFIX = struct.Struct('<12sQQ')
MAX_RECEIPT_BYTES = 2 * 1024**2
MAX_PAYLOAD_BYTES = 32 * 1024**2


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def _keys(context):
    return tuple(sorted((kind, t, width) for kind in ('on', 'off')
        for t in range(len(context.bank)) for width in core.M37_SPECTRAL_WIDTHS))


def _binding(run):
    if not isinstance(run, pipeline.NativeRun):
        raise ValueError('direct synthetic native run required')
    # Reconstruct metadata checks from actual typed sources, not mutable source_ids.
    current = pipeline.NativeRun(run.context, run.sources)
    if current.source_ids != run.source_ids or current.modelled_bytes != run.modelled_bytes:
        raise ValueError('native run source inventory or memory declaration changed')
    payload_bytes = len(_keys(run.context)) * 3 * run.context.grid.support_bin_count * 4
    # Snapshot + legacy arrays + read/write staging + one epoch/native audit row.
    additional = 3 * payload_bytes + len(run.context.bank) * run.context.grid.support_bin_count * 4
    if (payload_bytes > MAX_PAYLOAD_BYTES
            or current.modelled_bytes + additional > run.context.memory_limit_bytes):
        raise core.V0P6CapacityError('score handoff payload or modeled buffer cap exceeded')
    return {'context_sha256': run.context.identity,
        'direct_factor_contract_sha256': run.context.factor_contract.identity,
        'source_ids': dict(current.source_ids),
        'legacy_modeled_array_bytes': current.modelled_bytes,
        'additional_modeled_array_bytes': additional,
        'source_domain': 'synthetic', 'telescope_values_opened': False,
        'scientific_candidate_selection_authorized': False}


def _audit(run, store):
    binding = _binding(run)
    pipeline.NativeRun.validate_store(run, store)
    keys = _keys(run.context)
    if set(store.arrays) != set(keys) or set(store.expected_ids) != set(keys):
        raise ValueError('exact direct score vector inventory required')
    provenance = store.provenance
    fields = {'schema', 'context_sha256', 'direct_factor_contract_sha256', 'source_ids',
        'native_caches', 'modelled_array_bound_bytes', 'source_domain', 'telescope_values_opened'}
    if (set(provenance) != fields
            or provenance['schema'] != 'radio-direct-native-score-inventory-v1'
            or provenance['telescope_values_opened'] is not False
            or provenance['modelled_array_bound_bytes'] != binding['legacy_modeled_array_bytes']):
        raise ValueError('exact synthetic native score provenance required')
    values = {key: checked_vectors(store, *key, run.context.grid) for key in keys}
    entries = provenance['native_caches']
    expected = [(scan, width) for scan in run.context.scans for width in core.M37_SPECTRAL_WIDTHS]
    if not isinstance(entries, list) or len(entries) != len(expected):
        raise ValueError('complete ordered native cache inventory required')
    for entry, (scan, width) in zip(entries, expected):
        if (set(entry) != {'scan', 'width', 'source_identity', 'cache_identity',
                          'full_support_score_sha256'}
                or entry['scan'] != scan['label'] or type(entry['width']) is not int
                or entry['width'] != width
                or entry['source_identity'] != binding['source_ids'][scan['label']]):
            raise ValueError('native cache inventory ancestry differs')
        for name in ('cache_identity', 'full_support_score_sha256'):
            core._frozen_sha256(entry[name], name)
        h = hashlib.sha256()
        for t in range(len(run.context.bank)):
            h.update(np.ascontiguousarray(values[scan['kind'], t, width][scan['epoch'] - 1]).tobytes())
        if h.hexdigest() != entry['full_support_score_sha256']:
            raise ValueError('native cache score digest differs from reconstructed vectors')
    return binding, keys, values, json.loads(canonical(provenance))


@dataclass(frozen=True)
class SealedScoreStore:
    receipt_json: bytes
    payloads: tuple

    @property
    def identity(self):
        return sha(self.receipt_json)

    @property
    def record(self):
        return json.loads(self.receipt_json)

    @property
    def provenance(self):
        return self.record['provenance']

    @property
    def arrays(self):
        record = self.record
        return MappingProxyType({tuple(v['key']): np.frombuffer(p, dtype='<f4').reshape(record['shape'])
            for v, p in zip(record['vectors'], self.payloads)})

    @property
    def expected_ids(self):
        return MappingProxyType({tuple(v['key']): v['legacy_vector_id'] for v in self.record['vectors']})

    def get(self, kind, t, width):
        key = kind, t, width
        array = self.arrays[key]
        actual = native.digest({'provenance': self.provenance, 'key': list(key),
                                'payload': native.array_hash(array)})
        if actual != self.expected_ids[key]:
            raise ValueError('sealed score payload changed')
        return array, actual


def _validate_parts(run, receipt_json, payloads, trusted_receipt_sha256):
    core._frozen_sha256(trusted_receipt_sha256, 'caller-held score receipt')
    if (type(receipt_json) is not bytes or len(receipt_json) > MAX_RECEIPT_BYTES
            or sha(receipt_json) != trusted_receipt_sha256):
        raise ValueError('score receipt differs from independent caller pin')
    record = json.loads(receipt_json)
    binding = _binding(run)
    keys = _keys(run.context)
    shape = [3, run.context.grid.support_bin_count]
    if (canonical(record) != receipt_json
            or set(record) != {'schema', 'binding', 'shape', 'dtype', 'vectors', 'provenance'}
            or record['schema'] != SCHEMA or record['binding'] != binding
            or record['shape'] != shape or record['dtype'] != '<f4'
            or not isinstance(record['vectors'], list) or len(record['vectors']) != len(keys)
            or type(payloads) is not tuple or len(payloads) != len(keys)):
        raise ValueError('score receipt layout or native binding differs')
    for key, v, payload in zip(keys, record['vectors'], payloads):
        if (type(payload) is not bytes or len(payload) != shape[0] * shape[1] * 4
                or set(v) != {'key', 'payload_sha256', 'legacy_vector_id'}
                or v['key'] != list(key) or v['payload_sha256'] != sha(payload)):
            raise ValueError('ordered score vector bytes or receipt differ')
        core._frozen_sha256(v['legacy_vector_id'], 'legacy vector identity')
    snapshot = SealedScoreStore(receipt_json, payloads)
    _audit(run, snapshot)
    return snapshot


def seal_native_store(run, store):
    """Production boundary only; store must be the freshly returned native result.

    This checks reconciliation, not an independently authorized producer. A
    caller must retain the returned receipt pin separately for later restoration.
    """
    binding, keys, values, provenance = _audit(run, store)
    payloads = tuple(values[k].tobytes(order='C') for k in keys)
    vectors = [{'key': list(k), 'payload_sha256': sha(p),
        'legacy_vector_id': native.digest({'provenance': provenance, 'key': list(k), 'payload': sha(p)})}
        for k, p in zip(keys, payloads)]
    receipt = canonical({'schema': SCHEMA, 'binding': binding,
        'shape': [3, run.context.grid.support_bin_count], 'dtype': '<f4',
        'vectors': vectors, 'provenance': provenance})
    return _validate_parts(run, receipt, payloads, sha(receipt))


class GuardedRun(pipeline.NativeRun):
    """Opt-in synthetic wrapper; no telescope or altered numerical implementation."""
    def build_store(self):
        return seal_native_store(self, super().build_store())

    def validate_store(self, store):
        if type(store) is not SealedScoreStore:
            raise ValueError('receipt-bound sealed score store required')
        _validate_parts(self, store.receipt_json, store.payloads, store.identity)

    def restore(self, path, *, trusted_receipt_sha256):
        return load_checkpoint(path, self, trusted_receipt_sha256=trusted_receipt_sha256)


def _sync_directory(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_checkpoint(path, run, snapshot, *, trusted_receipt_sha256, checkpoint=lambda stage: None):
    if type(snapshot) is not SealedScoreStore:
        raise ValueError('sealed score snapshot required')
    _validate_parts(run, snapshot.receipt_json, snapshot.payloads, trusted_receipt_sha256)
    path = Path(path)
    # Destination parent is a caller-controlled local directory, not receipt input.
    if path.exists() or path.is_symlink():
        raise FileExistsError('immutable score checkpoint already exists')
    fd, temporary = tempfile.mkstemp(prefix='.score-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(PREFIX.pack(MAGIC, len(snapshot.receipt_json), sum(map(len, snapshot.payloads))))
            output.write(snapshot.receipt_json)
            for payload in snapshot.payloads:
                output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        checkpoint('temporary_fsynced')
        # hard-link installation is exclusive and atomic on the same filesystem.
        os.link(temporary, path, follow_symlinks=False)
        checkpoint('installed')
        _sync_directory(path.parent)
        checkpoint('directory_fsynced')
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    # Confirmation is a fresh bounded read using the same external pin.
    restored = load_checkpoint(path, run, trusted_receipt_sha256=trusted_receipt_sha256)
    return {'schema': 'radio-local-score-checkpoint-confirmation-v1',
        'receipt_sha256': restored.identity, 'file_bytes': path.stat().st_size,
        'telescope_admission_issued': False}


def load_checkpoint(path, run, *, trusted_receipt_sha256):
    core._frozen_sha256(trusted_receipt_sha256, 'caller-held score receipt')
    _binding(run)
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    fd = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('regular immutable score checkpoint required')
    except BaseException:
        os.close(fd)
        raise
    with os.fdopen(fd, 'rb') as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('regular immutable score checkpoint required')
        if before.st_size < PREFIX.size:
            raise ValueError('truncated score checkpoint prefix')
        prefix = source.read(PREFIX.size)
        if len(prefix) != PREFIX.size:
            raise ValueError('truncated score checkpoint prefix')
        magic, receipt_size, payload_size = PREFIX.unpack(prefix)
        expected_bytes = len(_keys(run.context)) * 3 * run.context.grid.support_bin_count * 4
        if (magic != MAGIC or not 0 < receipt_size <= MAX_RECEIPT_BYTES
                or payload_size != expected_bytes or payload_size > MAX_PAYLOAD_BYTES
                or before.st_size != PREFIX.size + receipt_size + payload_size):
            raise ValueError('score checkpoint length, version or resource bound differs')
        receipt = source.read(receipt_size)
        if len(receipt) != receipt_size or sha(receipt) != trusted_receipt_sha256:
            raise ValueError('score receipt differs from independent caller pin')
        # Validate bounded metadata before reading payload, with no path dispatch.
        record = json.loads(receipt)
        if (canonical(record) != receipt or record.get('binding') != _binding(run)
                or record.get('shape') != [3, run.context.grid.support_bin_count]
                or len(record.get('vectors', [])) != len(_keys(run.context))):
            raise ValueError('checkpoint receipt context or layout differs')
        each = 3 * run.context.grid.support_bin_count * 4
        payloads = tuple(source.read(each) for _ in _keys(run.context))
        after = os.fstat(source.fileno())
        if (source.read(1) or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError('score checkpoint changed during read')
    return _validate_parts(run, receipt, payloads, trusted_receipt_sha256)
