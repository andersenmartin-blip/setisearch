"""Coherent post-normalization native translations, never telescope attestations.

For epoch e and both ON/OFF scans, D_e(row,k)=B_e(row,k+s_e).
There is no circular wrap, interpolation or change of normalization. Filter
translation commutes exactly with every complete fixed float32 window. Derived
source/cache types deliberately differ from the original telescope types.
"""
import math
from types import SimpleNamespace

import numpy as np

from . import search_v0p6 as core
from .detector_m43u import digest
from .injection_m43r import NativeOverlay, ScoreStore

CONTRACT = 'm43af-normalized-native-positive-translation-v1'


class TranslatedReceiver:
    def __init__(self, original, shifts):
        if (len(shifts) != 3 or shifts[0] != 0 or
                any(type(s) is not int or s < 0 for s in shifts)):
            raise ValueError('three nonnegative integer native shifts, first zero, required')
        self.original = original
        self.shifts = tuple(shifts)
        self.sources, self.caches = {}, {}

    def cache(self, label, width):
        if (label, width) in self.caches:
            return self.caches[label, width]
        if label not in {f'epoch{e}_{kind}' for e in (1, 2, 3) for kind in ('on', 'off')}:
            raise ValueError('unknown source')
        old = self.original.cache(label, width)
        s = self.shifts[int(label[5])-1]
        if s >= old.source.geometry.channel_count-2*(width//2):
            raise core.V0P6CoverageError('translation removes complete native support')
        if label not in self.sources:
            src = old.source
            g = core.NativeFrequencyGeometry(raw_zero_hz=src.geometry.raw_zero_hz,
                channel_width_hz=src.geometry.channel_width_hz,
                channel_count=src.geometry.channel_count-s)
            spec = dict(contract=CONTRACT, parent_source_identity=src.identity,
                        scan=label, native_shift=s, remaining_channels=g.channel_count)
            self.sources[label] = SimpleNamespace(geometry=g, integration_count=src.integration_count,
                values=src.values[:, s:], identity=digest(spec), provenance=spec,
                source_family='derived-normalized-native-translation')
        source = self.sources[label]
        values = old.values[:, s:]
        if values.flags.writeable or source.values.flags.writeable:
            raise ValueError('immutable parent/native cache required')
        if values.shape != (source.integration_count, source.geometry.channel_count-2*(width//2)):
            raise ValueError('translated cache shape mismatch')
        self.caches[label, width] = SimpleNamespace(source=source, width=width, values=values,
            identity=digest(dict(contract=CONTRACT, parent_cache_identity=old.identity,
                                 derived_source_identity=source.identity, width=width)),
            cache_family='derived-normalized-native-translation')
        return self.caches[label, width]


class NativeShiftOverlay(NativeOverlay):
    """Reuse original receiver arithmetic against explicit derived native views."""
    def __init__(self, original_receiver, shifts, bank, table, basis, grid):
        self.receiver = TranslatedReceiver(original_receiver, shifts)
        self.bank, self.table, self.basis, self.grid = bank, table, basis, grid
        self.factors, self.joint_indices, self.patches = {}, {}, {}
        arrays, inventory = {}, []
        for kind in ('on', 'off'):
            for e in range(3):
                label = f'epoch{e+1}_{kind}'
                f = core.factor_table_for_scan(table, basis, label)
                if kind == 'on':
                    self.factors[e] = f
                src = self.receiver.cache(label, 1).source
                idx = core.nearest_native_indices(src.geometry, f[:, :, None]*grid.support_hz)
                self.joint_indices[kind, e] = idx
                # Covers every possible tracked or stationary +/-100 Hz query,
                # every width, and all retained/profile support coordinates.
                margin = 129//2+math.ceil(100/src.geometry.channel_width_hz)+4
                if idx.min() < margin or idx.max() >= src.geometry.channel_count-margin:
                    raise core.V0P6CoverageError('translated complete pipeline support unavailable')
                for w in core.M37_SPECTRAL_WIDTHS:
                    cache = self.receiver.cache(label, w)
                    summed = np.zeros((len(bank), grid.support_bin_count), dtype='<f4')
                    for row in range(src.integration_count):
                        summed += cache.values[row, idx[:, row, :]-w//2]
                    summed /= np.float32(math.sqrt(src.integration_count))
                    for t in range(len(bank)):
                        key = kind, t, w
                        if key not in arrays:
                            arrays[key] = np.empty((3, grid.support_bin_count), dtype='<f4')
                        arrays[key][e] = summed[t]
                    inventory.append(dict(scan=label, width=w, derived_source=src.identity,
                                          derived_cache=cache.identity))
        provenance = dict(contract=CONTRACT, shifts=list(shifts), derived_inventory=inventory,
                          operator='B(row,k+s); shared ON/OFF shift per epoch; no wrap',
                          grid_sha256=core.proxy_carrier_grid_sha256(grid),
                          catalogue_sha256=table.template_bank_sha256)
        self.overlay_receipt = dict(schema=CONTRACT, components=[], sources=[], patch_payloads={},
                                    background_provenance=provenance)
        self.baseline = ScoreStore(arrays, provenance)

    def trial(self, components):
        if components:
            raise ValueError('null translation cannot contain injected components')
        return self.baseline

    def __call__(self, records, bank, table):
        if bank != self.bank or table.factor_table_sha256 != self.table.factor_table_sha256:
            raise ValueError('translated receiver catalogue mismatch')
        signatures, receipt = super().__call__(records, bank, table)
        receipt['source_family'] = CONTRACT
        return signatures, receipt
