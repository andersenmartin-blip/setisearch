"""Frozen fresh synthetic six-scan burst generator; no RNG or arrays at import."""
from __future__ import annotations

import hashlib
import math


def _uniform_convolution_cdf(x, intrinsic_width, sweep_width):
    import numpy as np
    a, b = float(intrinsic_width), float(sweep_width)
    if a <= 0 or b < 0 or not math.isfinite(a + b):
        raise ValueError('Finite positive intrinsic width and nonnegative sweep required')
    x = np.asarray(x, dtype=np.float64)
    if b == 0:
        return np.clip((x + a / 2) / a, 0., 1.)
    h = (a + b) / 2
    y = np.clip(x, -h, h)
    positive_square = lambda z: np.maximum(z, 0.) ** 2
    value = (positive_square(y + h) - positive_square(y + (b - a) / 2)
             - positive_square(y + (a - b) / 2) + positive_square(y - h)) / (2 * a * b)
    return np.where(x <= -h, 0., np.where(x >= h, 1., np.clip(value, 0., 1.)))


def _profile(layer, scan, geometry):
    import numpy as np
    loaded0, loaded1 = geometry['loaded_source_channel_interval']
    base = geometry['reference_source_channel_interval'][0] + float(layer['reference_native_offset'])
    times = np.asarray(scan['row_midpoints_seconds_from_tref'], dtype=np.float64)
    centers = base + float(layer['drift_hz_s']) * times / float(scan['df_hz'])
    channels = np.arange(loaded0, loaded1, dtype=np.float64)
    difference = channels[None, :] - centers[:, None]
    sweep = abs(float(layer['drift_hz_s'])) * float(scan['tsamp_s']) / abs(float(scan['df_hz']))
    profile = (_uniform_convolution_cdf(difference + .5, layer['intrinsic_width_channels'], sweep)
               - _uniform_convolution_cdf(difference - .5, layer['intrinsic_width_channels'], sweep))
    active = list(layer['active_source_rows'])
    if len(active) not in (1, 4) or len(set(active)) != len(active) or any(row not in range(16) for row in active):
        raise ValueError('One or four distinct active source rows required')
    keep = np.zeros(16, dtype=bool)
    keep[active] = True
    profile[~keep] = 0.
    if not np.isfinite(profile).all() or (profile < 0).any():
        raise ValueError('Analytic exposure kernel is invalid; no clipping or redraw')
    if not np.allclose(profile[active].sum(axis=1), 1., atol=1e-11, rtol=0):
        raise ValueError('Signal support leaves the frozen loaded channels')
    return profile, centers, sweep


def _ideal_projection(profile, centers, geometry, widths):
    import numpy as np
    channels = np.arange(*geometry['loaded_source_channel_interval'], dtype=np.int64)
    nearest = np.rint(centers).astype(np.int64)
    projections = []
    for width in widths:
        select = abs(channels[None, :] - nearest[:, None]) <= width // 2
        projections.append(float(profile[select].sum() / math.sqrt(4 * width)))
    winner = int(np.argmax(projections))
    if not math.isfinite(projections[winner]) or projections[winner] <= 0:
        raise ValueError('Positive noise-free burst projection required')
    return {'maximum': projections[winner], 'oracle_width_channels': int(widths[winner]),
            'by_width': dict(zip(map(str, widths), projections)), 'score_normalization_rows': 4}


def generate_case(case, contract):
    """Return ordered six float32 power arrays and JSON-ready truth after caller GO.

    This function does not admit execution, read telescope crops, write files,
    change identities, retry or draw replacement arrays. The caller owns freeze,
    source authentication, once-only claims and resource enforcement.
    """
    import numpy as np
    identity = case['case_id']
    if not identity.startswith('SETI_SIXSCAN_BURST_20261015_RECOVERY_V1:'):
        raise ValueError('Separate prospective six-scan identity required')
    if hashlib.sha256(identity.encode('ascii')).hexdigest() != case['seed_sha256']:
        raise ValueError('Complete identity/seed SHA256 differs')
    if case['noise_law'] != 'gamma16' or np.__version__ != contract['background']['numpy_version']:
        raise ValueError('Frozen Gamma16 and NumPy version required')
    geometry = contract['geometry']
    scans = geometry['scan_metadata']
    if len(scans) != 6 or [scan['role'] for scan in scans] != ['ON', 'OFF'] * 3:
        raise ValueError('Six chronological alternating scans required')
    nchan = geometry['loaded_source_channel_interval'][1] - geometry['loaded_source_channel_interval'][0]
    if nchan != 12096 or geometry['reference_source_channel_interval'][1] - geometry['reference_source_channel_interval'][0] != 4096:
        raise ValueError('Full declared source dimensions required')
    widths = tuple(contract['signal']['oracle_widths'])
    if widths != (1, 3, 9, 33):
        raise ValueError('Frozen oracle widths required')
    # All geometric signal layers and amplitudes are fixed before creating RNG.
    layers_by_scan = [[] for _ in scans]
    layer_truth = []
    fluxes = {}
    primary_indices = []
    for layer in case['signal_layers']:
        index = int(layer['scan_index'])
        if index not in range(6):
            raise ValueError('Layer scan index outside the cadence')
        scan = scans[index]
        profile, centers, sweep = _profile(layer, scan, geometry)
        projection = _ideal_projection(profile, centers, geometry, widths)
        level = float(layer['nominal_ideal_box_score'])
        if level <= 0 or not math.isfinite(level):
            raise ValueError('Finite positive prescribed ideal amplitude required')
        flux = .25 * level / projection['maximum']
        layers_by_scan[index].append(flux * profile)
        window = list(layer['truth_window_source_rows'])
        if len(window) != 4 or window != list(range(window[0], window[0] + 4)):
            raise ValueError('Explicit complete four-row truth window required')
        record = {'scan_id': scan['scan_id'], 'scan_index': index, 'kind': layer['kind'],
                  'active_source_rows': list(layer['active_source_rows']), 'truth_window_source_rows': window,
                  'truth_window_first_time_from_tref_s': float(scan['row_midpoints_seconds_from_tref'][window[0]]),
                  'truth_window_last_time_from_tref_s': float(scan['row_midpoints_seconds_from_tref'][window[-1]]),
                  'true_continuous_absolute_centers': centers.tolist(),
                  'true_nearest_even_absolute_centers': np.rint(centers).astype(np.int64).tolist(),
                  'drift_hz_s': float(layer['drift_hz_s']), 'reference_native_offset': float(layer['reference_native_offset']),
                  'reference_source_channel': float(geometry['reference_source_channel_interval'][0] + layer['reference_native_offset']),
                  'reference_frequency_hz': float(scan['fch1_hz'] + (geometry['reference_source_channel_interval'][0] + layer['reference_native_offset']) * scan['df_hz']),
                  'intrinsic_width_channels': int(layer['intrinsic_width_channels']), 'integration_sweep_width_channels': sweep,
                  'mean_integration_frequency_summed_positive_power': flux,
                  'nominal_ideal_box_score': level, 'ideal_box_projection_per_unit_power': projection['maximum'],
                  'injection_oracle_width_channels': projection['oracle_width_channels'],
                  'ideal_box_projection_by_width': projection['by_width'], 'score_normalization_rows': 4}
        layer_truth.append(record)
        if layer['kind'] == 'PRIMARY':
            if index in primary_indices:
                raise ValueError('Duplicate primary signal in one scan')
            primary_indices.append(index)
            fluxes[scan['scan_id']] = record
    if primary_indices != case['active_scan_indices']:
        raise ValueError('Primary layer activity differs from fixed recipe')
    rng = np.random.Generator(np.random.PCG64(int(case['seed_sha256'], 16)))
    arrays = []
    for index, scan in enumerate(scans):
        if scan['nrows'] != 16:
            raise ValueError('All complete sixteen-row scans required')
        power = rng.gamma(shape=16., scale=.0625, size=(16, nchan))
        for added in layers_by_scan[index]:
            power += added
        if not np.isfinite(power).all() or (power <= 0).any():
            raise ValueError('Frozen synthetic power failed positive-finite check; no redraw')
        raw = power.astype(np.dtype('<f4'))
        if not np.isfinite(raw).all() or (raw <= 0).any():
            raise ValueError('Float32 source representation failed; no redraw')
        arrays.append(raw)
    truth = {'case_id': identity, 'family': case['family'], 'synthetic': True,
             'seed_sha256': case['seed_sha256'], 'noise_law': 'gamma16',
             'primary_active_scan_indices': primary_indices, 'active_scan_indices': primary_indices,
             'active_ON_scan_ids': [scans[index]['scan_id'] for index in primary_indices if scans[index]['role'] == 'ON'],
             'flux_by_scan': fluxes, 'layer_truth': layer_truth, 'single_row_diagnostic_denominator_rows': 4,
             'raw_array_dtype': '<f4', 'raw_array_shape_each_scan': [16, nchan],
             'signal_oracles_computed_before_RNG': True, 'physical_SNR_flux_or_FAP_established': False}
    if case['drift_hz_s'] is not None:
        scan0 = scans[0]
        channel = geometry['reference_source_channel_interval'][0] + float(case['reference_native_offset'])
        truth.update(reference_source_channel=channel, reference_frequency_hz=float(scan0['fch1_hz'] + channel * scan0['df_hz']),
                     drift_hz_s=float(case['drift_hz_s']), intrinsic_width_channels=int(case['intrinsic_width_channels']),
                     nominal_ideal_box_score=float(case['nominal_ideal_box_score']))
    return arrays, truth
