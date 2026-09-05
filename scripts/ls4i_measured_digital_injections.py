#!/usr/bin/env python3
"""Frozen measured-background experiment with separate digital amplitude axes."""
from __future__ import annotations

import gzip
import hashlib
import itertools
import json
from pathlib import Path
import platform
import shutil
import tempfile
import types

import numpy as np

from seti_repeater import light_sail as ls
from seti_repeater.light_sail_residual import channel_indices, residual_metrics, compare_residuals
from ls4b_filterbank_screen import channel_bounds, parse_and_validate_header as medium_header
from ls4c_htr_followup import parse_and_validate_header as htr_header
from ls4f_v2_native_reanalysis import download_exact, numeric_agreement
from ls4g_synthetic_recovery import truth_matches
from ls4h_transfer_preflight import integrated_boxes

ROOT = Path(__file__).resolve().parents[1]


def encoded(x):
    return (json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False) + '\n').encode()


def write_json(path, x):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_bytes(encoded(x))
    temp.replace(path)


def verify_freeze():
    for line in (ROOT / 'LS4I_FREEZE.sha256').read_text().splitlines():
        expected, name = line.split('  ', 1)
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'freeze mismatch: {name}')


def search_kwargs(detector):
    return dict(base_bin_channels=detector['base_bin_native_channels'], spectral_width_bins=detector['spectral_width_base_bins'],
                duration_s=detector['duration_s'], minimum_score=detector['off_veto_score_threshold'],
                maximum_events=detector['maximum_events_per_scan'], clip_low=detector['native_robust_clip'][0],
                clip_high=detector['native_robust_clip'][1], minimum_valid_fraction=detector['minimum_valid_fraction'])


def coarse_parameters(kwargs):
    return tuple(kwargs[k] for k in ('base_bin_channels', 'clip_low', 'clip_high', 'minimum_valid_fraction'))


def cached_search(coarse, valid, frequency, dt, kwargs):
    """Run the original search bytecode with only native preprocessing cached.

    A private globals dictionary prevents changes to the detector module.
    The stub is never read as data: the validated callback supplies coarse bins.
    """
    def cached(values, *parameters):
        if parameters != coarse_parameters(kwargs) or values.shape != (len(coarse), len(frequency)):
            raise ValueError('cached geometry or settings differ')
        return coarse, valid
    if not np.all(np.diff(frequency) > 0):
        raise ValueError('cache requires ascending frequencies')
    namespace = {**ls.search_broadband_events.__globals__, '_coarse_normalized_spectrum': cached}
    search = types.FunctionType(ls.search_broadband_events.__code__, namespace)
    stub = np.broadcast_to(np.zeros((len(coarse), 1), dtype=np.float32), (len(coarse), len(frequency)))
    return search(stub, frequency, dt, **kwargs)


def trial_specs(config, include_zero=False):
    for fi, wi, width, amplitude in itertools.product(range(len(config['frequency_centers_mhz'])),
            range(len(config['envelopes_s'])), config['pulse_widths_s'],
            ([0.] if include_zero else config['medium_amplitudes'])):
        yield {'frequency_index': fi, 'window_index': wi, 'pulse_width_s': width, 'medium_amplitude': amplitude}


def truth_geometry(spec, config):
    center = config['frequency_centers_mhz'][spec['frequency_index']]
    start, stop = config['envelopes_s'][spec['window_index']]
    return {'frequency_start_mhz': center - config['bandwidth_mhz']/2,
            'frequency_stop_mhz': center + config['bandwidth_mhz']/2, 'time_start_s': start, 'time_stop_s': stop}


def profile(n, dt, spec, config):
    truth = truth_geometry(spec, config)
    start, stop = truth['time_start_s'], truth['time_stop_s']
    boxes = [(start, stop, config['envelope_height'])]
    width = spec['pulse_width_s']
    boxes += [(start + t - width/2, start + t + width/2, config['pulse_height']) for t in config['pulse_offsets_s']]
    return integrated_boxes(n, dt, boxes)


def bilateral_overlap(a, b, c, d):
    return max(0., min(b, d) - max(a, c)) / max(b-a, d-c) if b > a and d > c else 0.


def associated(event, truth, threshold):
    return all(bilateral_overlap(event[f'{axis}_start_{unit}'], event[f'{axis}_stop_{unit}'],
                                 truth[f'{axis}_start_{unit}'], truth[f'{axis}_stop_{unit}']) >= threshold
               for axis, unit in [('frequency', 'mhz'), ('time', 's')])


def modified_coarse(data, frequency, base_coarse, base_valid, shape, truth, amplitude, kwargs):
    """Re-normalize every affected complete native bin after digital injection."""
    size = kwargs['base_bin_channels']
    mask = (frequency >= truth['frequency_start_mhz']) & (frequency <= truth['frequency_stop_mhz'])
    coarse, valid = base_coarse.copy(), base_valid.copy()
    for index in sorted(set((np.flatnonzero(mask) // size).tolist())):
        if index >= coarse.shape[1]:
            continue  # Original detector discards incomplete final native bin.
        sl = slice(index*size, (index+1)*size)
        block = np.asarray(data[:, sl], dtype=np.float32).copy()
        selected = mask[sl]
        _, sigma = ls._robust_location_scale(block, axis=0)
        safe = selected & np.isfinite(sigma) & (sigma > np.finfo(np.float32).eps)
        block[:, safe] = (block[:, safe].astype(np.float64) + amplitude * shape[:, None] * sigma[safe]).astype(np.float32)
        c, v = ls._coarse_normalized_spectrum(block, *coarse_parameters(kwargs))
        coarse[:, index], valid[index] = c[:, 0], v[0]
    return coarse, valid


def matched_events(search, off_search, truth, detector, config):
    if search['retention_truncated'] or off_search['retention_truncated']:
        raise ValueError('event retention truncation; no complete recovery conclusion')
    candidates = ls.apply_abacad_veto([
        {'label': 'A1', 'role': 'ON', 'adjacent_off_labels': ['B1'], 'search': search},
        {'label': 'B1', 'role': 'OFF', 'adjacent_off_labels': [], 'search': off_search}],
        on_threshold=detector['on_score_threshold'], off_threshold=detector['off_veto_score_threshold'],
        minimum_frequency_overlap=detector['off_veto_frequency_overlap'])
    matches = [c for c in candidates if associated(c['event'], truth, config['association_min_fraction_of_both_intervals'])]
    if len(matches) > config['resource']['max_associated_events_per_trial']:
        raise ValueError('associated event cap exceeded')
    return matches


def read_medium(path, source, config, old, historical, off_search=None):
    scan = next(s for s in old['selected_sequence'] if s['label'] == source['label'])
    header, offset = medium_header(path, scan, old)
    detector = old['medium_resolution_screen']
    first, last = channel_bounds(header['fch1'], header['foff'], header['nchans'], *detector['science_band_mhz'])
    matrix = np.memmap(path, mode='r', dtype='<f4', offset=offset, shape=(old['expected_filterbank_header']['ntime'], header['nchans']))
    data = matrix[:, first:last][:, ::-1]
    frequency = (header['fch1'] + np.arange(first, last) * header['foff'])[::-1]
    kwargs = search_kwargs(detector)
    coarse, valid = ls._coarse_normalized_spectrum(data, *coarse_parameters(kwargs))
    baseline = cached_search(coarse, valid, frequency, header['tsamp'], kwargs)
    expected = next(s for s in historical['scans'] if s['label'] == source['label'])['search']
    if not numeric_agreement(baseline, expected, **config['replay_tolerance']):
        raise ValueError(f'historical medium replay differs: {source["label"]}')
    trials = []
    if source['label'] == 'A1':
        for spec in trial_specs(config):
            truth = truth_geometry(spec, config)
            shape = profile(len(data), header['tsamp'], spec, config)
            c, v = modified_coarse(data, frequency, coarse, valid, shape, truth, spec['medium_amplitude'], kwargs)
            search = cached_search(c, v, frequency, header['tsamp'], kwargs)
            matches = matched_events(search, off_search, truth, detector, config)
            trials.append({**spec, 'truth': truth, 'search': search, 'matched_events': matches})
            print(f'medium injected {len(trials)}/{config["expected_medium_injected_trials"]}: matched {len(matches)}', flush=True)
    del data, matrix
    return {'label': source['label'], 'historical_replay_agrees': True, 'baseline_search': baseline, 'trials': trials}


def event_band(event, header, config):
    padding = config['htr_frequency_padding_mhz']
    indices = channel_indices(header['fch1_mhz'], header['foff_mhz'], header['nchans'],
                              event['frequency_start_mhz']-padding, event['frequency_stop_mhz']+padding)
    return (int(indices[0]), int(indices[-1])+1)


def collect_bands(trials, baseline_matches, config, header):
    bands = set()
    for spec in trial_specs(config, include_zero=True):
        truth = truth_geometry(spec, config)
        # Unpadded injection band is always extracted for reference scaling and labelled fixed-window diagnostics.
        indices = channel_indices(header['fch1_mhz'], header['foff_mhz'], header['nchans'], truth['frequency_start_mhz'], truth['frequency_stop_mhz'])
        bands.add((int(indices[0]), int(indices[-1])+1))
    for trial in trials + baseline_matches:
        for m in trial['matched_events']:
            bands.add(event_band(m['event'], header, config))
    if len(bands) > config['resource']['max_unique_htr_bands']:
        raise ValueError('HTR band cap exceeded')
    return sorted(bands)


def read_htr(path, source, old, bands, config):
    scan = next(s for s in old['sources'] if s['label'] == source['label'])
    header, offset = htr_header(path, scan, old)
    n, channels = old['expected_filterbank_header']['ntime'], header['nchans']
    matrix = np.memmap(path, mode='r', dtype=np.uint8, offset=offset, shape=(n, channels))
    series = {band: np.empty(n) for band in bands}
    for first in range(0, n, config['resource']['chunk_rows']):
        stop = min(n, first + config['resource']['chunk_rows'])
        for band, values in series.items():
            values[first:stop] = matrix[first:stop, band[0]:band[1]].mean(axis=1, dtype=np.float64)
    del matrix
    return series


def residual_record(on, off_metrics, dt, event, truth_times, width, settings):
    metrics = residual_metrics(on, dt, event['time_start_s'], event['time_stop_s'], settings)
    comparison = compare_residuals(metrics, off_metrics, settings)
    truth = [{'center_s': t, 'width_s': width} for t in truth_times]
    matches = {s['requested_width_s']: truth_matches(s['inside_pulses'], truth, s['effective_width_s'], dt) for s in metrics['scales']}
    matched = max((len(matches[s['widths_s'][0]] & matches[s['widths_s'][1]]) for s in comparison['supporting_scale_pairs']), default=0)
    return {'passed': comparison['residual_pulse_pattern_pass'], 'truth_associated_pass': comparison['residual_pulse_pattern_pass'] and matched >= settings['minimum_separated_pulses'],
            'cross_scale_supported': bool(comparison['supporting_scale_pairs']), 'matched_truth_pulses': matched,
            'off_veto': comparison['off_pulse_veto'], 'reference_veto': comparison['on_reference_pulse_veto'],
            'on_inside_counts': [len(s['inside_pulses']) for s in metrics['scales']],
            'on_reference_counts': [len(s['reference_pulses']) for s in metrics['scales']],
            'off_counts': [len(s['inside_pulses'])+len(s['reference_pulses']) for s in off_metrics['scales']]}


def evaluate_htr(on, off, trials, baselines, config, header, settings):
    dt, n = header['tsamp_s'], header['ntime']
    centers = (np.arange(n)+.5)*dt
    off_cache = {}
    def evaluate(spec, match, amplitude, fixed=False):
        truth = truth_geometry(spec, config)
        tidx = channel_indices(header['fch1_mhz'], header['foff_mhz'], header['nchans'], truth['frequency_start_mhz'], truth['frequency_stop_mhz'])
        truth_band = (int(tidx[0]), int(tidx[-1])+1)
        event = truth if fixed else match['event']
        band = truth_band if fixed else event_band(event, header, config)
        ref = (centers < truth['time_start_s'] - settings['reference_guard_s']) | (centers >= truth['time_stop_s'] + settings['reference_guard_s'])
        reference = on[truth_band][ref]
        sigma = float(1.4826*np.median(np.abs(reference-np.median(reference))))
        if not np.isfinite(sigma) or sigma <= np.finfo(float).eps:
            raise ValueError('degenerate measured injection scale')
        fraction = max(0, min(band[1], truth_band[1])-max(band[0], truth_band[0])) / (band[1]-band[0])
        injected = on[band] + amplitude*sigma*fraction*profile(n, dt, spec, config)
        key = (band, event['time_start_s'], event['time_stop_s'])
        if key not in off_cache:
            off_cache[key] = residual_metrics(off[band], dt, event['time_start_s'], event['time_stop_s'], settings)
        times = [truth['time_start_s'] + t for t in config['pulse_offsets_s']]
        record = residual_record(injected, off_cache[key], dt, event, times, spec['pulse_width_s'], settings)
        return {**record, 'band_indices': band, 'event_window_s': [event['time_start_s'], event['time_stop_s']],
                'injection_reference_scale_counts': sigma, 'injected_channel_fraction': fraction}
    baseline_rows = []
    for spec in baselines:
        records = [{**evaluate(spec, m, 0.), 'stage1_off_survives': m['survives_adjacent_off_veto']} for m in spec['matched_events']]
        baseline_rows.append({**{k:spec[k] for k in ('frequency_index','window_index','pulse_width_s')}, 'events': records,
                              'joint_pass': any(r['stage1_off_survives'] and r['truth_associated_pass'] for r in records)})
    paired = []
    for index, trial in enumerate(trials):
        for amplitude in config['htr_amplitudes']:
            records = [{**evaluate(trial, m, amplitude), 'stage1_off_survives': m['survives_adjacent_off_veto']} for m in trial['matched_events']]
            baseline = next(b for b in baseline_rows if all(b[k]==trial[k] for k in ('frequency_index','window_index','pulse_width_s')))
            joint = any(r['stage1_off_survives'] and r['truth_associated_pass'] for r in records)
            paired.append({**{k:trial[k] for k in ('frequency_index','window_index','pulse_width_s','medium_amplitude')},
                           'htr_amplitude': amplitude, 'stage1_matched_count': len(records),
                           'stage1_survivor_count': sum(r['stage1_off_survives'] for r in records),
                           'events': records, 'joint_digital_pass': joint, 'uninjected_joint_pass': baseline['joint_pass'],
                           'joint_pass_absent_in_uninjected_baseline': joint and not baseline['joint_pass']})
        print(f'HTR followed Stage-1 trial {index+1}/{len(trials)}', flush=True)
    fixed_rows = []
    for spec in trial_specs(config, include_zero=True):
        for amplitude in config['htr_amplitudes']:
            fixed_rows.append({**spec, 'htr_amplitude': amplitude, **evaluate(spec, None, amplitude, fixed=True)})
    return {'paired_configurations': paired, 'uninjected_baselines': baseline_rows, 'fixed_window_diagnostics': fixed_rows}


def main():
    verify_freeze()
    config = json.loads((ROOT / 'config/ls4i_measured_digital_injections.json').read_text())
    for name, expected in config['input_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'input changed: {name}')
    old = json.loads((ROOT / 'config/ls4b_lhs1140_x_light_sail.json').read_text())
    oldh = json.loads((ROOT / 'config/ls4c_lhs1140_x_htr_followup.json').read_text())
    historical = json.loads((ROOT / 'results_ls4b/screen.json').read_text())
    settings = json.loads((ROOT / 'config/ls4e_residual_qualification.json').read_text())['settings']
    output = ROOT / 'results_ls4i_measured_digital_injections'
    output.mkdir(exist_ok=False)
    rawdir = Path(tempfile.mkdtemp(prefix='setisearch-ls4i-', dir=config['resource']['raw_directory_parent']))
    if ROOT in rawdir.resolve().parents:
        raise ValueError('raw directory must be outside workspace')
    receipts, medium, htr, baselines = [], {}, {}, []
    charged_bytes = 0
    try:
        bands = None
        for source in config['sources']:
            path = rawdir / 'source.fil'
            errors = []
            for attempt in range(config['resource']['attempts_per_source']):
                charged_bytes += source['source_size_bytes']
                if charged_bytes > config['resource']['max_total_download_bytes']:
                    raise ValueError('download budget exceeded')
                try:
                    receipt = download_exact(source, path, config)
                    break
                except Exception as exc:
                    errors.append(str(exc))
                    if attempt+1 == config['resource']['attempts_per_source']:
                        raise
            receipt.update({'label': source['label'], 'product': source['product'], 'prior_attempt_errors': errors})
            try:
                if source['product'] == 'medium_resolution':
                    record = read_medium(path, source, config, old, historical,
                                         medium.get('B1', {}).get('baseline_search'))
                    medium[source['label']] = record
                    write_json(output / f'{source["label"]}_medium.json', record)
                    if source['label'] == 'A1':
                        for spec in trial_specs(config, include_zero=True):
                            baselines.append({**spec, 'matched_events': matched_events(record['baseline_search'], medium['B1']['baseline_search'],
                                truth_geometry(spec, config), old['medium_resolution_screen'], config)})
                        bands = collect_bands(record['trials'], baselines, config, oldh['expected_filterbank_header'])
                        print(f'HTR extraction inventory: {len(bands)} unique bands', flush=True)
                else:
                    htr[source['label']] = read_htr(path, source, oldh, bands, config)
            finally:
                path.unlink(missing_ok=True)
                path.with_suffix('.part').unlink(missing_ok=True)
            receipt['raw_file_deleted'] = True
            receipts.append(receipt)
            write_json(output / 'source_receipts.json', {'sources': receipts, 'charged_download_bytes': charged_bytes})
            print(f'processed and deleted {source["label"]} {source["product"]}', flush=True)
        result = evaluate_htr(htr['A1'], htr['B1'], medium['A1']['trials'], baselines, config, oldh['expected_filterbank_header'], settings)
        if len(result['paired_configurations']) != config['expected_paired_digital_configurations'] or len(result['fixed_window_diagnostics']) != config['expected_fixed_window_htr_diagnostics']:
            raise ValueError('incomplete grid')
        result.update({'artifact_type': 'seti_repeater.ls4i_measured_digital_injection_result', 'version': 1,
                       'status': 'measured-digital-study-complete', 'reserved_sources_opened': False,
                       'same_physical_injection_across_products': False, 'astronomical_completeness': False,
                       'new_candidate_search_claimed': False, 'raw_spectral_arrays_published': False,
                       'source_bytes_verified': sum(s['source_size_bytes'] for s in config['sources']),
                       'freeze_sha256': hashlib.sha256((ROOT / 'LS4I_FREEZE.sha256').read_bytes()).hexdigest(),
                       'python_version': platform.python_version(), 'numpy_version': np.__version__})
        result['result_sha256'] = hashlib.sha256(encoded(result)).hexdigest()
        write_json(output / 'injections.json', result)
        for name in ['A1_medium.json', 'B1_medium.json']:
            p = output / name
            (output / (name+'.gz')).write_bytes(gzip.compress(p.read_bytes(), mtime=0))
            p.unlink()
        print(json.dumps({'status': result['status'], 'paired_passes': sum(r['joint_digital_pass'] for r in result['paired_configurations']), 'result_sha256': result['result_sha256']}), flush=True)
    except Exception as exc:
        write_json(output / 'abort.json', {'status': 'aborted-no-complete-conclusion', 'error': str(exc),
                                          'completed_sources': receipts, 'charged_download_bytes': charged_bytes})
        raise
    finally:
        shutil.rmtree(rawdir)


if __name__ == '__main__':
    main()
