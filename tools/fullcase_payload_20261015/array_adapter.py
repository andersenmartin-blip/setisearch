"""NPY-in-ZIP transport with one-array-at-a-time memory and full byte checking."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np


def input_hash(array):
    # Empty (0,4) OFF inventories are valid transports, not missing results.
    return hashlib.sha256(memoryview(array).cast('B') if array.nbytes else b'').hexdigest()


class PhysicalCap:
    def __init__(self, stream, cap): self.stream, self.cap, self.count = stream, cap, 0
    def write(self, block):
        if self.count + len(block) > self.cap:
            raise ValueError('NPZ physical writer cap exhausted; retain partial')
        written = self.stream.write(block); self.count += written; return written
    def tell(self): return self.count
    def flush(self): self.stream.flush()


def write_arrays(path, specs, make_array, budget, physical_cap=None):
    descriptors = []
    with budget.writer(path) as target:
        output = PhysicalCap(target, physical_cap) if physical_cap is not None else target
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
            for spec in specs:
                array = make_array(spec)
                if (array.dtype.str != spec['dtype'] or list(array.shape) != spec['shape'] or
                        array.dtype.hasobject or not array.flags.c_contiguous or
                        array.nbytes != spec['nbytes']):
                    raise ValueError('Producer input array differs from fixed descriptor')
                input_sha = input_hash(array)
                with archive.open(spec['key'] + '.npy', 'w', force_zip64=True) as stream:
                    np.lib.format.write_array(stream, array, version=(1, 0), allow_pickle=False)
                info = archive.getinfo(spec['key'] + '.npy')
                if info.file_size > spec['nbytes'] + 4096:
                    raise ValueError('NPY member exceeds declared header/body allowance')
                descriptors.append({**spec, 'C_order_input_sha256': input_sha,
                                    'NPY_uncompressed_bytes': info.file_size})
                del array
    return descriptors


def verify_arrays(path, descriptors, expected_specs):
    if len(descriptors) != len(expected_specs):
        raise ValueError('Array descriptor census differs')
    total = 0
    with zipfile.ZipFile(path) as archive:
        names = [s['key'] + '.npy' for s in expected_specs]
        if archive.namelist() != names or len(set(archive.namelist())) != len(names):
            raise ValueError('NPZ member names/order/census differ')
        for descriptor, spec in zip(descriptors, expected_specs):
            if any(descriptor.get(k) != v for k, v in spec.items()):
                raise ValueError('Array path, shape, dtype or source geometry differs')
            info = archive.getinfo(spec['key'] + '.npy')
            if (info.flag_bits & 1 or info.file_size != descriptor['NPY_uncompressed_bytes'] or
                    info.file_size > spec['nbytes'] + 4096):
                raise ValueError('NPZ uncompressed byte bound differs')
            with archive.open(info) as stream:
                if np.lib.format.read_magic(stream) != (1, 0):
                    raise ValueError('Unexpected NPY version')
                shape, fortran, dtype = np.lib.format.read_array_header_1_0(stream, max_header_size=4096)
                if (list(shape) != spec['shape'] or dtype.str != spec['dtype'] or
                        dtype.hasobject or fortran):
                    raise ValueError('NPY header shape/dtype/order differs')
                h = hashlib.sha256(); remaining = spec['nbytes']
                while remaining:
                    block = stream.read(min(1 << 20, remaining))
                    if not block: raise ValueError('Truncated NPY body')
                    h.update(block); remaining -= len(block)
                if stream.read(1): raise ValueError('Extra bytes after NPY body')
                if h.hexdigest() != descriptor['C_order_input_sha256']:
                    raise ValueError('Input/decoded raw array bytes differ')
                total += spec['nbytes']
    return {'arrays_verified': len(expected_specs), 'all_raw_array_bytes_verified': total,
            'header_and_every_body_byte_checked': True,
            'scientific_integrity_or_QA_established': False}


def load_typed_array(path, descriptor):
    """Optional consumer adapter; only after full transport verification."""
    with zipfile.ZipFile(path) as archive:
        with archive.open(descriptor['key'] + '.npy') as stream:
            array = np.lib.format.read_array(stream, allow_pickle=False, max_header_size=4096)
    if (array.dtype.str != descriptor['dtype'] or list(array.shape) != descriptor['shape'] or
            input_hash(array) != descriptor['C_order_input_sha256']):
        raise ValueError('Consumer typed array differs')
    return array


def load_case_field(folder, path):
    """One typed numeric field at a time, preserving its explicit source path."""
    folder = Path(folder)
    entries = json.loads((folder / 'CASE_ARRAYS.json').read_text())['arrays']
    matches = [d for d in entries if d['path'] == path]
    if len(matches) != 1: raise ValueError('Missing/ambiguous case field path')
    return load_typed_array(folder / 'case_arrays.npz', matches[0])
