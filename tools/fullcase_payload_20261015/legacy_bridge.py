"""Descriptor ABI bridge only; does not execute or authorize scientific QA."""
import numpy as np

from array_adapter import load_typed_array


def legacy_descriptor(descriptor):
    return {'array_descriptor': {
        'npz_key': descriptor['key'], 'shape': descriptor['shape'],
        'dtype': str(np.dtype(descriptor['dtype'])),
        'C_order_bytes_sha256': descriptor['C_order_input_sha256'],
        'nbytes': descriptor['nbytes'], 'original_field_path': descriptor['path']}}


class TypedStore:
    def __init__(self, npz_path, descriptors):
        self.path = npz_path
        self.entries = {d['key']: d for d in descriptors}
        if len(self.entries) != len(descriptors): raise ValueError('Duplicate array key')

    def __getitem__(self, key):
        return load_typed_array(self.path, self.entries[key])
