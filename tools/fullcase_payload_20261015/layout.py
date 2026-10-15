"""Analytical storage geometry, from public source definitions only."""
from __future__ import annotations

import math
import numpy as np


def specs(inventory_rows=2000000):
    out = []
    def add(path, shape, dtype, kind):
        dt = np.dtype(dtype)
        out.append({'key': f'A{len(out):06d}', 'path': path, 'shape': list(shape),
                    'dtype': dt.str, 'nbytes': math.prod(shape) * dt.itemsize,
                    'kind': kind, 'pattern_serial': len(out)})
    for scan in range(6):
        add(['inputs', str(scan), 'raw_power'], (16, 12096), '<f4', 'raw')
    maps = [
        ('scores', (5,), '<f8'), ('widths', (5,), '<i2'),
        ('window_starts', (5,), '<i2'), ('drift_grid_indices', (5,), '<i4'),
        ('retained_valid', (5,), '|b1'), ('native4_centers', (5, 4), '<i8'),
        ('drift_alias_first_index', (5,), '<i4'), ('drift_alias_last_index', (5,), '<i4'),
        ('reference_source_channels', (), '<i8'),
        ('total_original_hypothesis_count', (), '<i8'),
        ('total_unique_native_hypothesis_count', (), '<i8'),
        ('valid_original_hypothesis_count', (), '<i8'),
        ('valid_unique_native_hypothesis_count', (), '<i8'),
        ('maximum_robust_box_track_score', (), '<f8')]
    for scan in range(6):
        n = 4096 if scan % 2 == 0 else 6652
        for name, tail, dtype in maps:
            add(['scan_maps', str(scan), name], (n, *tail), dtype, 'map')
        for name in ('row_power_median', 'row_residual_median', 'row_residual_MAD_scale',
                     'row_winsorized_residual_location'):
            add(['scan_maps', str(scan), 'normalization', name], (16,), '<f8', 'normalization')
        add(['scan_maps', str(scan), 'normalization', 'normalization_source_channels'],
            (4096,), '<i8', 'normalization')
        add(['scan_maps', str(scan), 'normalization', 'normalization_unmasked_counts'],
            (16,), '<i8', 'normalization')
    inventory = ('reference_carrier_index', 'reference_source_channel', 'width', 'window_start',
                 'representative_drift_index', 'alias_first_index', 'alias_last_index', 'score',
                 'native4_centers')
    for scan in (1, 3, 5):
        for name in inventory:
            shape = (inventory_rows, 4) if name == 'native4_centers' else (inventory_rows,)
            add(['OFF_threshold_inventories', str(scan), name], shape,
                '<f8' if name == 'score' else '<i8', 'OFF_inventory')
    add(['geometry', 'drift_grid_hz_s'], (5723,), '<f8', 'geometry')
    for scan in range(6):
        add(['geometry', 'times_from_tref_s', str(scan)], (16,), '<f8', 'geometry')
        for window in range(0, 13, 2):
            for parity in (0, 1):
                prefix = ['alias_geometry', str(scan), str((window, parity))]
                add(prefix + ['relative_centers'], (5723, 4), '<i8', 'alias')
                add(prefix + ['alias_first_index'], (5723,), '<i4', 'alias')
                add(prefix + ['alias_last_index'], (5723,), '<i4', 'alias')
                add(prefix + ['drift_to_unique_path'], (5723,), '<i4', 'alias')
    # Explicit bit fixtures in addition to the source-derived layout, not science.
    add(['engineering_edge_bits', 'float64'], (6,), '<f8', 'edge')
    add(['engineering_edge_bits', 'float32'], (6,), '>f4', 'edge')
    return out


def storage_bounds(items):
    counts = {}
    for spec in items:
        counts[spec['kind']] = counts.get(spec['kind'], 0) + spec['nbytes']
    raw = sum(s['nbytes'] for s in items)
    # Each actual NPY member/header is checked against this allowance. ZIP is
    # also physically bounded by the shared writer; no entropy guarantee used.
    npz_writer_cap = raw + len(items) * 4096 + 65536
    bundle_cap = (npz_writer_cap + 128 * 1024**2 + 3 * 1024**2 + 65536)
    return {'array_count_including_two_edge_arrays': len(items),
            'source_layout_array_count': len(items)-2, 'raw_bytes_by_kind': counts,
            'all_array_raw_bytes': raw, 'NPZ_physical_writer_cap_bytes': npz_writer_cap,
            'per_case_conditional_bundle_cap_bytes': bundle_cap,
            'metadata_unpacked_cap_bytes': 128 * 1024**2,
            'case_cap_is_enforced_not_a_compression_or_completion_guarantee': True,
            'legacy_3GiB_bytes_comparison_only': 3 * 1024**3,
            'complete_case_slots_at_that_bound': (3 * 1024**3) // bundle_cap,
            '428_slots_at_bound_bytes': 428 * bundle_cap,
            '428_slots_admitted_in_3GiB': 428 * bundle_cap <= 3 * 1024**3}


def values(spec):
    """Deterministic transport patterns, never simulated telescope samples."""
    dt = np.dtype(spec['dtype']); n = math.prod(spec['shape'])
    if spec['kind'] == 'edge':
        if dt.itemsize == 8:
            bits = np.array([0, 1 << 63, 0x3ff0000000000001,
                             0x7ff8000000000042, 0x7ff0000000000000, 0xfff0000000000000], dtype='<u8')
        else:
            bits = np.array([0, 1 << 31, 0x3f800001, 0x7fc00042,
                             0x7f800000, 0xff800000], dtype='>u4')
        return bits.view(dt).reshape(spec['shape'])
    base = (np.arange(n, dtype=np.int64) % 6652) + spec['pattern_serial']
    if dt.kind == 'b':
        arr = (base % 2 == 0)
    elif dt.kind == 'f':
        arr = (1 + (base % 1024) / 1024).astype(dt)
    else:
        arr = (base % 30000).astype(dt)
    shaped = arr.reshape(spec['shape'])
    return shaped if shaped.flags.c_contiguous else shaped.copy(order='C')
