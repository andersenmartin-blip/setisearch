"""Prospective BP synthetic inputs; importing this module never draws random values.

All powers are synthetic. Exposure intervals are centered on declared sample
times, a convention that makes no claim about the telescope header semantics.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROWS = 16
CHANNELS = 1_048_576
BLOCK = 4096
DT = 18.253611008
DF = -2.7939677238464355
REFERENCE_CHANNEL = 64 * BLOCK + BLOCK // 2 + 0.5
HEADER_MJD = (57642.735972222225, 57642.73994212963,
              57642.74390046296, 57642.74791666667,
              57642.751921296294, 57642.75582175926)
SCAN_SECONDS = tuple((t - HEADER_MJD[0]) * 86400.0 for t in HEADER_MJD)
SEEDS = tuple(range(2026103001, 2026103009))
RATES = np.linspace(-4.0, 4.0, 839, dtype=np.float64)
ON_SCANS = (0, 2, 4)
NULL_LINE_Q = (63, 65, 127, 129)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def powers_sha256(raw):
    require(raw.dtype == np.dtype('<f4') and raw.flags.c_contiguous,
            'Exact C-order little-endian float32 powers required')
    return hashlib.sha256(memoryview(raw).cast('B')).hexdigest()


def file_sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _mad_rows(raw, q):
    values = raw[:, q * BLOCK:(q + 1) * BLOCK]
    center = np.median(values, axis=1)
    scale = np.median(np.abs(values - center[:, None]), axis=1) * np.float32(1.4826)
    require(center.dtype == np.float32 and scale.dtype == np.float32,
            'MAD arithmetic changed dtype')
    require(np.isfinite(scale).all() and np.all(scale > 0), 'Invalid preinjection MAD')
    return center, scale


def _truth(rate_index, width, present_scans):
    return {'channel_scan0_at_row7p5': REFERENCE_CHANNEL,
            'rate_index': rate_index, 'intrinsic_width': width,
            'present_scans': list(present_scans)}


def cases():
    """Return all 24 case identities in the immutable prospective order."""
    out = []
    for seed_index in range(1, 9):
        out.append({'case_id': f'N{seed_index:02d}', 'kind': 'null',
                    'base_seed_index': seed_index, 'truth': None,
                    'active_scans': [], 'rate_index': None,
                    'intrinsic_width': None, 'amplitude': None})
    for rate_index in (0, 419, 838):
        for width in (1, 9):
            for amplitude in (15, 256):
                index = len(out) - 7
                out.append({'case_id': f'P{index:02d}', 'kind': 'positive',
                            'base_seed_index': 3, 'rate_index': rate_index,
                            'intrinsic_width': width, 'amplitude': amplitude,
                            'active_scans': list(ON_SCANS),
                            'truth': _truth(rate_index, width, ON_SCANS)})
    for case_id, rate_index, present_scans in (
            ('A01', 419, range(6)), ('A02', 629, range(6)), ('A03', 419, (0,))):
        out.append({'case_id': case_id, 'kind': 'association',
                    'base_seed_index': 4, 'rate_index': rate_index,
                    'intrinsic_width': 1, 'amplitude': 256,
                    'active_scans': list(present_scans),
                    'truth': _truth(rate_index, 1, present_scans)})
    out.append({'case_id': 'A04', 'kind': 'association_broad',
                'base_seed_index': 4, 'rate_index': 419,
                'intrinsic_width': 1025, 'amplitude': None,
                'active_scans': list(range(6)),
                'truth': _truth(419, 1025, range(6)),
                'broad_gain': 16.0, 'row_interval': [4, 12],
                'channel_interval': [264192 - 512, 264192 + 513]})
    for case in out:
        case['id'] = case['case_id']
    return out


def specification():
    """Serializable recipe fixed before the first RNG call or search score."""
    return {
        'schema': 'SETI_BP_SYNTHETIC_RECIPES_V1',
        'shape': [ROWS, CHANNELS], 'dtype': '<f4', 'C_order': True,
        'numpy_version': '2.3.5', 'generator': 'Generator(PCG64(SeedSequence(seed).spawn(6)[scan]))',
        'seeds': list(SEEDS), 'scan_order': list(range(6)),
        'one_distribution_call_per_scan': True,
        'requested_variates_per_scan': ROWS * CHANNELS,
        'primitive_bitgenerator_draw_count': 'Not inferred: gamma/exponential samplers can consume a variable number; full states are saved.',
        'distribution_call': {
            'seed_indices_1_2': 'rng.exponential(scale=128.0,size=(16,1048576)) float64, then one <f4 cast',
            'seed_indices_3_4': 'rng.gamma(shape=8.0,scale=16.0,size=(16,1048576)) float64, then one <f4 cast',
            'seed_indices_5_6': 'same gamma; multiply float64 by (1+0.25*c/(N-1)), then by (1+0.015*r), then one <f4 cast',
            'seed_indices_7_8': 'same gamma; multiply columns >=262144 by1.25 in float64, then one <f4 cast; add fixed lines described below',
        },
        'fixed_null_lines': {'seed_indices': [7, 8], 'q': list(NULL_LINE_Q),
                             'center': 'q*4096+2048+0.5', 'rate_hz_s': 0,
                             'intrinsic_width': 1, 'all_six_scans': True,
                             'integrated_amplitude_MAD': 20,
                             'MAD': 'Each row of this q in immutable gained pre-line float32 base; float32 median, deviations and 1.4826 multiplication.',
                             'addition': 'Exactly half integrated excess into each of the two neighboring integer channels; float64 addition followed by one float32 cast.'},
        'dt_seconds': DT, 'df_hz': DF, 'header_tstart_mjd': list(HEADER_MJD),
        'scan_reference_seconds_from_scan0': list(SCAN_SECONDS),
        'row_epoch': '(row-7.5)*dt relative to each scan reference',
        'exposure_interval': 'row-center time plus [-dt/2,+dt/2]; synthetic convention only',
        'reference_center': REFERENCE_CHANNEL,
        'reference_definition': 'Integer middle channel q64*4096+2048 plus subchannel phase0.5, in scan0 row7.5 coordinates',
        'propagation': 'reference_center+(rate/df)*((header_tstart_scan-header_tstart_scan0)*86400)',
        'positive_amplitude_definition': 'Total integrated excess power in each row = amplitude * that scan row preinjection q64 block MAD; not a peak-height amplitude.',
        'preinjection_MAD': 'Float32 median/MAD of base[:,262144:266240], factor np.float32(1.4826); computed from immutable un-injected scan for both methods.',
        'line_profile': 'Width-normalized top-hat translated linearly over one exposure; exact piecewise-linear channel-overlap integral using breakpoint trapezoids, float64.',
        'rounding': 'float32(float64(base_pixel)+float64(delta_pixel)) once; no intermediate delta rounding',
        'mass_bound_before_rounding': '256*float64_epsilon*max(1,total_integrated_power) per row',
        'quantization_bound_per_pixel': '0.5*float32_spacing(rounded_positive_pixel)+8*float64_epsilon*max(1,abs(exact_float64_sum))',
        'injection_evidence': 'Sparse row/channel, float64 delta, float32 resulting values, baseline/common-input hashes and complete preinjection MAD coefficients. Full injected arrays are reconstructed in memory and write-protected.',
        'broad_association': 'All6 scans rows4..11, channels263680..264704 inclusive, positive delta15*base, yielding gain16 with a single float32 rounding. Same stationary reference center; no claim of narrow-line truth.',
        'cases': cases(),
    }


def truth_geometry(case, scan):
    require(scan in range(6), 'Invalid scan index')
    truth = case.get('truth')
    if truth is None:
        return None
    rate = float(RATES[int(truth['rate_index'])])
    center = float(truth['channel_scan0_at_row7p5'] + rate / DF * SCAN_SECONDS[scan])
    row_centers = center + rate / DF * ((np.arange(ROWS, dtype=np.float64) - 7.5) * DT)
    return {**truth, 'scan': scan, 'rate_hz_s': rate,
            'reference_center': center, 'row_centers': row_centers.tolist(),
            'scan_reference_seconds': SCAN_SECONDS[scan],
            'injection_present': scan in truth['present_scans'],
            'exposure_channel_displacement': rate / DF * DT}


def integrated_channel_weights(center, intrinsic_width, channel_displacement):
    """Integrate a unit-mass drifting top-hat over one centered exposure.

Spatial cells have edges integer-channel +/-0.5. The overlap is piecewise
linear in the signal center, so trapezoids at its exact breakpoints are exact
apart from float64 arithmetic. This is independent of the search kernel.
"""
    center = float(center)
    width = float(intrinsic_width)
    displacement = float(channel_displacement)
    require(math.isfinite(center) and math.isfinite(width) and width > 0
            and math.isfinite(displacement), 'Invalid profile geometry')
    span = abs(displacement)
    start, stop = center - span / 2.0, center + span / 2.0
    lo = int(math.floor(start - width / 2.0 - 0.5))
    hi = int(math.ceil(stop + width / 2.0 + 0.5))
    channels = np.arange(lo, hi + 1, dtype=np.int64)
    # Express local distances relative to each channel to avoid subtraction
    # of large squared absolute coordinates in a CDF formula.
    relative_center = center - channels.astype(np.float64)
    a = relative_center - span / 2.0
    b = relative_center + span / 2.0
    half = width / 2.0
    if span == 0.0:
        weights = np.maximum(0.0, np.minimum(a + half, 0.5) - np.maximum(a - half, -0.5)) / width
    else:
        knots = np.stack((a, b,
                          np.clip(np.full_like(a, -0.5 - half), a, b),
                          np.clip(np.full_like(a, -0.5 + half), a, b),
                          np.clip(np.full_like(a, 0.5 - half), a, b),
                          np.clip(np.full_like(a, 0.5 + half), a, b)), axis=1)
        knots.sort(axis=1)
        overlap = np.maximum(0.0, np.minimum(knots + half, 0.5) - np.maximum(knots - half, -0.5))
        area = np.sum((knots[:, 1:] - knots[:, :-1]) * (overlap[:, 1:] + overlap[:, :-1]) * 0.5, axis=1)
        weights = area / (span * width)
    keep = weights > 0.0
    channels, weights = channels[keep], weights[keep]
    require(np.isfinite(weights).all() and np.all(weights >= 0), 'Invalid integrated profile')
    mass = math.fsum(float(v) for v in weights)
    require(abs(mass - 1.0) <= 256 * np.finfo(np.float64).eps,
            f'Profile mass is not conserved: {mass}')
    return channels, weights


def _save_npy_exclusive(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        np.save(stream, raw, allow_pickle=False)


def _add_sparse(raw, rows, channels, deltas):
    """Apply one rounded addition per unique pixel and report conservative bounds."""
    require(len(rows) == len(channels) == len(deltas), 'Sparse lengths differ')
    keys = rows.astype(np.int64) * raw.shape[1] + channels
    require(len(np.unique(keys)) == len(keys), 'Repeated injection pixel')
    require(np.all(rows >= 0) and np.all(rows < raw.shape[0]) and
            np.all(channels >= 0) and np.all(channels < raw.shape[1]), 'Injection unsupported')
    require(np.isfinite(deltas).all() and np.all(deltas >= 0), 'Negative/nonfinite delta')
    previous = raw[rows, channels].astype(np.float64)
    exact = previous + deltas
    rounded = exact.astype(np.float32)
    require(np.isfinite(rounded).all(), 'Injection overflow')
    errors = np.abs(rounded.astype(np.float64) - exact)
    bounds = (0.5 * np.spacing(rounded).astype(np.float64)
              + 8 * np.finfo(np.float64).eps * np.maximum(1.0, np.abs(exact)))
    require(np.all(errors <= bounds), 'Float32 quantization bound failed')
    raw[rows, channels] = rounded
    return rounded, {'pixels': len(rows), 'max_rounding_error': float(errors.max(initial=0.0)),
                     'sum_absolute_rounding_error': float(math.fsum(errors.tolist())),
                     'sum_rounding_error_bound': float(math.fsum(bounds.tolist())),
                     'quantization_bound_pass': True}


def generate_base_scan(seed_index, scan, output_path):
    """The sole RNG entry point. Root must freeze/publicly read back before calling."""
    require(np.__version__ == '2.3.5', 'NumPy version differs from frozen generator')
    require(seed_index in range(1, 9) and scan in range(6), 'Invalid seed/scan')
    output_path = Path(output_path)
    require(not output_path.exists(), 'Base output already exists')
    seed = SEEDS[seed_index - 1]
    sequence = np.random.SeedSequence(seed).spawn(6)[scan]
    rng = np.random.Generator(np.random.PCG64(sequence))
    before = copy.deepcopy(rng.bit_generator.state)
    if seed_index <= 2:
        values = rng.exponential(scale=128.0, size=(ROWS, CHANNELS))
        distribution = 'exponential(scale=128.0)'
    else:
        values = rng.gamma(shape=8.0, scale=16.0, size=(ROWS, CHANNELS))
        distribution = 'gamma(shape=8.0,scale=16.0)'
    after = copy.deepcopy(rng.bit_generator.state)
    if seed_index in (5, 6):
        gain = 1.0 + 0.25 * np.arange(CHANNELS, dtype=np.float64) / (CHANNELS - 1)
        values *= gain[None, :]
        values *= (1.0 + 0.015 * np.arange(ROWS, dtype=np.float64))[:, None]
    elif seed_index in (7, 8):
        values[:, 64 * BLOCK:] *= 1.25
    raw = values.astype('<f4')
    del values
    null_line_records = []
    if seed_index in (7, 8):
        for q in NULL_LINE_Q:
            medians, scales = _mad_rows(raw, q)
            channels = np.tile(np.array([q * BLOCK + BLOCK // 2,
                                         q * BLOCK + BLOCK // 2 + 1], dtype=np.int64), ROWS)
            rows = np.repeat(np.arange(ROWS, dtype=np.int64), 2)
            delta = np.repeat(scales.astype(np.float64) * 20.0 * 0.5, 2)
            _, rounding = _add_sparse(raw, rows, channels, delta)
            null_line_records.append({'q': q, 'preline_medians': medians.tolist(),
                                      'preline_MAD_scales': scales.tolist(), 'rounding': rounding})
    require(np.isfinite(raw).all() and np.all(raw >= 0), 'Invalid base powers')
    payload_hash = powers_sha256(raw)
    _save_npy_exclusive(output_path, raw)
    raw.setflags(write=False)
    return {'seed_index': seed_index, 'seed': seed, 'scan': scan,
            'spawn_key': list(sequence.spawn_key), 'seed_sequence_entropy': sequence.entropy,
            'generator': 'PCG64', 'numpy_version': np.__version__,
            'state_before': before, 'state_after': after, 'distribution': distribution,
            'distribution_calls': 1, 'requested_variates': ROWS * CHANNELS,
            'primitive_draw_count': None,
            'primitive_draw_count_note': 'Not inferred for rejection/variable-consumption distribution samplers',
            'shape': [ROWS, CHANNELS], 'dtype': '<f4', 'powers_sha256': payload_hash,
            'file_sha256': file_sha256(output_path), 'file_bytes': output_path.stat().st_size,
            'path': str(output_path), 'fixed_null_lines': null_line_records}


def prepare_injected_scan(base_path, case, scan, delta_path=None):
    """Return shared read-only input and reconstructible sparse injection evidence.

The caller saves the returned receipt. For null/absent scans the base file is
mapped read-only. Active cases create one C-contiguous in-memory copy; only
sparse delta evidence is written, never a second full input file.
"""
    require(scan in range(6), 'Invalid scan')
    require(case in cases(), 'Case differs from frozen recipes')
    base_path = Path(base_path)
    base = np.load(base_path, mmap_mode='r', allow_pickle=False)
    require(base.shape == (ROWS, CHANNELS) and base.dtype == np.dtype('<f4')
            and base.flags.c_contiguous and not base.flags.writeable, 'Invalid base array')
    require(np.isfinite(base).all() and np.all(base >= 0), 'Invalid base powers')
    base_hash = powers_sha256(base)
    base_file_hash = file_sha256(base_path)
    baseline_receipt = json.loads(base_path.with_suffix('.json').read_text())
    require(baseline_receipt['seed_index'] == case['base_seed_index']
            and baseline_receipt['scan'] == scan, 'Wrong frozen base identity')
    require(baseline_receipt['file_sha256'] == base_file_hash
            and baseline_receipt['powers_sha256'] == base_hash
            and baseline_receipt['file_bytes'] == base_path.stat().st_size,
            'Base receipt digest or size mismatch')
    receipt = {'case_id': case['case_id'], 'scan': scan, 'base_path': str(base_path),
               'base_file_sha256': base_file_hash, 'base_powers_sha256': base_hash,
               'shape': [ROWS, CHANNELS], 'dtype': '<f4', 'geometry': truth_geometry(case, scan),
               'injected': scan in case['active_scans']}
    if not receipt['injected']:
        receipt.update({'common_input_powers_sha256': base_hash, 'delta_path': None,
                        'input_is_read_only': True, 'requested_injected_power': 0.0})
        return base, receipt
    require(delta_path is not None and not Path(delta_path).exists(), 'New sparse delta path required')
    raw = np.array(base, dtype='<f4', order='C', copy=True)
    medians, scales = _mad_rows(base, 64)
    receipt.update({'preinjection_q64_medians': medians.tolist(),
                    'preinjection_q64_MAD_scales': scales.tolist()})
    if case['kind'] == 'association_broad':
        row_grid, channel_grid = np.meshgrid(np.arange(*case['row_interval'], dtype=np.int64),
                                             np.arange(*case['channel_interval'], dtype=np.int64),
                                             indexing='ij')
        rows, channels = row_grid.ravel(), channel_grid.ravel()
        deltas = (case['broad_gain'] - 1.0) * base[rows, channels].astype(np.float64)
        receipt['mass_checks'] = {'profile': 'fixed_broad_multiplicative_gain',
                                  'gain': case['broad_gain'], 'row_interval': case['row_interval'],
                                  'channel_interval': case['channel_interval']}
    else:
        geometry = receipt['geometry']
        all_rows, all_channels, all_deltas, mass_checks = [], [], [], []
        for row, center in enumerate(geometry['row_centers']):
            channels_i, weights = integrated_channel_weights(center, case['intrinsic_width'],
                                                              geometry['exposure_channel_displacement'])
            expected = float(case['amplitude']) * float(scales[row])
            delta_i = weights * expected
            actual = math.fsum(float(v) for v in delta_i)
            bound = 256 * np.finfo(np.float64).eps * max(1.0, expected)
            require(abs(actual - expected) <= bound, 'Injection mass conservation failed')
            all_rows.append(np.full(len(channels_i), row, dtype=np.int64))
            all_channels.append(channels_i)
            all_deltas.append(delta_i)
            mass_checks.append({'row': row, 'expected_integrated_power': expected,
                                'actual_before_rounding': actual, 'absolute_error': abs(actual - expected),
                                'bound': bound, 'pass': True})
        rows, channels, deltas = (np.concatenate(values) for values in (all_rows, all_channels, all_deltas))
        receipt['mass_checks'] = mass_checks
    rounded, rounding = _add_sparse(raw, rows, channels, deltas)
    delta_path = Path(delta_path)
    delta_path.parent.mkdir(parents=True, exist_ok=True)
    with delta_path.open('xb') as stream:
        np.savez_compressed(stream, rows=rows, channels=channels,
                            delta_float64=deltas, resulting_float32=rounded)
    raw.setflags(write=False)
    receipt.update({'common_input_powers_sha256': powers_sha256(raw),
                    'delta_path': str(delta_path), 'delta_file_sha256': file_sha256(delta_path),
                    'delta_file_bytes': delta_path.stat().st_size, 'rounding': rounding,
                    'requested_injected_power': math.fsum(deltas.tolist()),
                    'input_is_read_only': True})
    require(powers_sha256(base) == base_hash, 'Immutable base was modified')
    return raw, receipt
