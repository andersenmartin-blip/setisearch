#!/usr/bin/env python3
"""Frozen, retrospective LS6 scan-end diagnostics; no change to acceptance."""
import hashlib
import json
from pathlib import Path

import numpy as np

from ls1_fetch import fetch
from ls4b_filterbank_screen import (atomic_write, channel_bounds,
    parse_and_validate_header, screen_scan, sha256_file)
from ls6_repaired_screen import seal
from seti_repeater.light_sail import _coarse_normalized_spectrum
from seti_repeater.search_v0p6 import canonical_json_bytes


def fit_trace(y, x):
    design = np.column_stack([np.ones(len(y)), x])
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    total = float(np.sum((y - np.mean(y)) ** 2))
    residual = float(np.sum((y - design @ beta) ** 2))
    return {'intercept': float(beta[0]), 'coefficient': float(beta[1]),
            'r_squared': 1 - residual / total if total > 0 else None}


def summarize_coarse(coarse, sample_time_s):
    valid = np.isfinite(coarse).all(axis=0)
    if not valid.any():
        raise RuntimeError('no fully valid coarse bins')
    values = np.asarray(coarse[:, valid], dtype=np.float64)
    common = np.median(values, axis=1)
    centered = values - values.mean(axis=0)
    shared = np.median(centered, axis=1)
    total = float(np.sum(centered ** 2))
    reduction = 1 - float(np.sum((centered - shared[:, None]) ** 2)) / total if total > 0 else None
    time = (np.arange(len(common)) + .5) * sample_time_s
    tails = []
    for n in (7, 15):
        if n >= len(common):
            raise ValueError('tail must be shorter than scan')
        delta = values[-n:].mean(axis=0) - values[:-n].mean(axis=0)
        step = (np.arange(len(common)) >= len(common) - n).astype(float)
        tails.append({'tail_samples': n, 'tail_start_s': (len(common)-n)*sample_time_s,
            'per_bin_mean_difference': delta.tolist(),
            'median_mean_difference': float(np.median(delta)),
            'positive_bin_count': int(np.sum(delta > 0)),
            'positive_bin_fraction': float(np.mean(delta > 0)),
            'step_fit': fit_trace(common, step)})
    return {'valid_bin_indices': np.flatnonzero(valid).tolist(),
        'coarse_normalized': [[float(x) if np.isfinite(x) else None for x in row] for row in coarse],
        'sample_midpoint_s': time.tolist(), 'frequency_median_trace': common.tolist(),
        'centered_frequency_median_trace': shared.tolist(),
        'unit_common_trace_energy_reduction': reduction,
        'linear_fit': fit_trace(common, time), 'tail_comparisons': tails}


def diagnose(data, sample_time_s, detector):
    coarse, fraction = _coarse_normalized_spectrum(data,
        detector['base_bin_native_channels'], *detector['native_robust_clip'],
        detector['minimum_valid_fraction'])
    result = summarize_coarse(coarse, sample_time_s)
    # Float64 and no clipping: independent raw-power sanity summary.
    raw = np.asarray(data, dtype=np.float64)
    median = np.nanmedian(raw, axis=0)
    good = np.isfinite(raw).all(axis=0) & np.isfinite(median) & (median > 0)
    if not good.any():
        raise RuntimeError('no positive finite native-channel medians')
    ratio = np.median(raw[:, good] / median[good], axis=1)
    result.update({'raw_relative_power_trace': ratio.tolist(),
        'raw_ratio_valid_channels': int(good.sum()),
        'raw_ratio_excluded_channels': int((~good).sum()),
        'raw_nonfinite_samples': int((~np.isfinite(raw)).sum()),
        'base_bin_valid_native_fraction': fraction.tolist()})
    return result


def run():
    config_path = Path('config/ls6a_scan_end.json')
    cfg = json.loads(config_path.read_text())
    config_hash = sha256_file(config_path)
    for path, digest in cfg['pinned_sha256'].items():
        if sha256_file(Path(path)) != digest:
            raise RuntimeError('frozen input or code changed: ' + path)
    original = json.loads(Path(cfg['original_config']).read_text())
    prior = json.loads(Path(cfg['original_result']).read_text())
    if prior['result_sha256'] != seal({k:v for k,v in prior.items() if k != 'result_sha256'}):
        raise RuntimeError('original result identity mismatch')
    out = Path('results_ls6a_scan_end'); out.mkdir(exist_ok=True)
    rawdir = Path('data_ls6a'); rawdir.mkdir(exist_ok=True)
    records = []
    for scan, old in zip(original['selected_sequence'], prior['scans'], strict=True):
        checkpoint = out / (scan['label'] + '.json')
        if checkpoint.exists():
            receipt = json.loads(checkpoint.read_text())
            if receipt['config_sha256'] != config_hash or receipt['checkpoint_sha256'] != seal({k:v for k,v in receipt.items() if k != 'checkpoint_sha256'}):
                raise RuntimeError('checkpoint integrity mismatch')
            if receipt['label'] != scan['label'] or receipt['source_sha256'] != old['source_sha256']:
                raise RuntimeError('checkpoint source mismatch')
        else:
            destination = rawdir / (scan['label'] + '.fil')
            try:
                digest = fetch(scan, destination)
                if digest != old['source_sha256']:
                    raise RuntimeError('original input checksum mismatch')
                local = {**original, 'expected_filterbank_header': scan['expected_filterbank_header']}
                replay = screen_scan(scan, local, destination, digest)
                if replay != old:
                    raise RuntimeError('original screen replay differs')
                header, offset = parse_and_validate_header(destination, scan, local)
                ntime = scan['expected_filterbank_header']['ntime']
                matrix = np.memmap(destination, dtype='<f4', mode='r', offset=offset,
                                   shape=(ntime, header['nchans']))
                det = original['medium_resolution_screen']
                start, stop = channel_bounds(header['fch1'], header['foff'], header['nchans'], *det['science_band_mhz'])
                data = np.array(matrix[:, start:stop], copy=True)
                del matrix
                if header['foff'] < 0:
                    data = data[:, ::-1].copy()
                receipt = {'label': scan['label'], 'role': scan['role'],
                    'config_sha256': config_hash, 'source_sha256': digest,
                    'source_url': old['source_url'], 'source_size_bytes': old['source_size_bytes'],
                    'original_screen_exactly_reproduced': True,
                    'diagnostic': diagnose(data, header['tsamp'], det)}
                del data
                receipt['checkpoint_sha256'] = seal(receipt)
                atomic_write(checkpoint, canonical_json_bytes(receipt))
            finally:
                destination.unlink(missing_ok=True)
                destination.with_suffix('.fil.part').unlink(missing_ok=True)
        records.append(receipt)
        print('verified diagnostic', scan['label'], flush=True)
    result = {'artifact_type': 'seti_repeater.ls6a_scan_end_diagnostic',
        'config_sha256': config_hash, 'original_result_identity': prior['result_sha256'],
        'retrospective': True, 'independent_confirmation': False,
        'primary_survivors_unchanged': prior['surviving_event_count'],
        'new_spectral_products_opened': 0, 'high_time_resolution_values_read': False,
        'technosignature_claimed': False, 'scans': records}
    result['result_sha256'] = seal(result)
    atomic_write(out / 'diagnostic.json', canonical_json_bytes(result))
    print('complete', result['result_sha256'], flush=True)


if __name__ == '__main__':
    run()
