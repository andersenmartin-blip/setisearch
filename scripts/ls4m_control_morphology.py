#!/usr/bin/env python3
"""Frozen retrospective B1 control morphology; no acceptance rule is changed."""
from __future__ import annotations

import gzip
import hashlib
import itertools
import json
from pathlib import Path
import platform
import shutil
import tempfile

import numpy as np

from ls4c_htr_followup import parse_and_validate_header
from ls4f_v2_native_reanalysis import download_exact
from ls4g_synthetic_recovery import verify_manifest
from ls4i_measured_digital_injections import encoded, write_json
from seti_repeater.light_sail_residual import residual_metrics, matched_pulses

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls4m_control_morphology'


def load(relative):
    path = ROOT / relative
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def geometry(record):
    return tuple(record['band_indices']) + tuple(record['event_window_s'])


def selections(previous):
    """Deduplicate measured windows, preserving every original use and veto."""
    selected = {}
    for ri, row in enumerate(previous['paired_configurations']):
        for ei, event in enumerate(row['events']):
            key = geometry(event)
            record = selected.setdefault(key, {'band_indices': list(key[:2]), 'event_window_s': list(key[2:]),
                'frequency_index': row['frequency_index'], 'uses': [], 'fixed_uses': []})
            if record['frequency_index'] != row['frequency_index'] or event['stage1_off_survives']:
                raise ValueError('inconsistent band identity or lost Stage-1 rejection')
            record['uses'].append({'row_index': ri, 'event_index': ei})
    for ri, event in enumerate(previous['fixed_window_diagnostics']):
        key = geometry(event)
        record = selected.setdefault(key, {'band_indices': list(key[:2]), 'event_window_s': list(key[2:]),
            'frequency_index': event['frequency_index'], 'uses': [], 'fixed_uses': []})
        record['fixed_uses'].append(ri)
    return [{'selection_id': i, **selected[key]} for i, key in enumerate(sorted(selected))]


def reference_mask(n, dt, window, guard):
    times = (np.arange(n) + .5) * dt
    return (times < window[0] - guard) | (times >= window[1] + guard)


def peak_sample_bounds(peak, width, dt, n):
    """Exact half-open sample-center interval, including machine rounding slack."""
    edges = np.array([peak - width / 2, peak + width / 2]) / dt - .5
    nearest = np.rint(edges)
    edges = np.where(np.abs(edges-nearest) < 1e-8, nearest, edges)
    lo, hi = np.ceil(edges).astype(int)
    return max(0, int(lo)), min(n, int(hi))


def concentration(block, baseline):
    """Descriptive positive channel excess over the full guarded reference mean."""
    if len(block) == 0:
        raise ValueError('empty peak block')
    excess = np.maximum(np.asarray(block, dtype=np.float64).mean(axis=0) - baseline, 0.)
    total = float(excess.sum())
    return {'positive_excess_counts_by_channel': excess.tolist(),
            'largest_channel_fraction': float(excess.max()/total) if total > 0 else None,
            'effective_positive_channels': float(total**2/np.square(excess).sum()) if total > 0 else None,
            'positive_channel_count': int(np.count_nonzero(excess)),
            'peak_sample_count': len(block)}


def replay_checks(records, previous):
    expected = selections(previous)
    if len(records) != len(expected):
        raise ValueError('incomplete selection inventory')
    selected_uses = fixed_uses = 0
    for record, selection in zip(records, expected):
        if any(record[k] != v for k, v in selection.items()):
            raise ValueError('changed or duplicated selection')
        metrics = record['residual_metrics']
        if metrics['envelope_s'] != selection['event_window_s']:
            raise ValueError('metric window changed')
        counts = [len(s['inside_pulses'])+len(s['reference_pulses']) for s in metrics['scales']]
        veto = any(counts)
        for use in selection['uses']:
            old = previous['paired_configurations'][use['row_index']]['events'][use['event_index']]
            if counts != old['off_counts'] or veto != old['off_veto'] or old['stage1_off_survives']:
                raise ValueError('selected control replay differs')
            selected_uses += 1
        for index in selection['fixed_uses']:
            old = previous['fixed_window_diagnostics'][index]
            if counts != old['off_counts'] or veto != old['off_veto']:
                raise ValueError('fixed control replay differs')
            fixed_uses += 1
    if (selected_uses, fixed_uses) != (256, 48):
        raise ValueError('incomplete replay use accounting')
    return {'selected_fragment_evaluations': selected_uses, 'fixed_window_evaluations': fixed_uses,
            'all_off_counts_and_vetoes_agree': True}


def analyse(path, source, old, selected, settings, resource, output):
    scan = next(s for s in old['sources'] if s['label'] == source['label'])
    header, offset = parse_and_validate_header(path, scan, old)
    n = old['expected_filterbank_header']['ntime']
    dt = header['tsamp']
    matrix = np.memmap(path, mode='r', dtype=np.uint8, offset=offset, shape=(n, header['nchans']))
    records, occupancy = [], []
    pulse_records = 0
    bands = sorted({tuple(s['band_indices']) for s in selected})
    for band in bands:
        # A narrow local copy is ephemeral; neither it nor a collapsed scan is published.
        native = np.empty((n, band[1]-band[0]), dtype=np.uint8)
        for first in range(0, n, resource['chunk_rows']):
            stop = min(n, first+resource['chunk_rows'])
            native[first:stop] = matrix[first:stop, band[0]:band[1]]
        values = native.mean(axis=1, dtype=np.float64)
        occupancy.append({'band_indices': list(band), 'sample_count_per_channel': n,
            'zero_byte_counts': (native == 0).sum(axis=0).tolist(),
            'max_byte_counts': (native == 255).sum(axis=0).tolist()})
        for selection in (s for s in selected if tuple(s['band_indices']) == band):
            window = selection['event_window_s']
            ref = reference_mask(n, dt, window, settings['reference_guard_s'])
            if ref.sum() < 32:
                raise ValueError('short reference')
            baseline = native[ref].mean(axis=0, dtype=np.float64)
            metrics = residual_metrics(values, dt, *window, settings)
            for scale in metrics['scales']:
                for region in ('inside_pulses', 'reference_pulses'):
                    for pulse in scale[region]:
                        pulse_records += 1
                        if pulse_records > resource['max_pulse_records']:
                            raise ValueError('pulse cap exceeded; no truncation permitted')
                        lo, hi = peak_sample_bounds(pulse['peak_time_s'], scale['effective_width_s'], dt, n)
                        if hi-lo != round(scale['effective_width_s']/dt):
                            raise ValueError('peak block geometry differs')
                        pulse['peak_channel_excess'] = concentration(native[lo:hi], baseline)
            records.append({**selection, 'residual_metrics': metrics,
                'reference_sample_count': int(ref.sum()), 'channel_reference_means': baseline.tolist()})
            # Persist derived evidence before replay validation and before raw deletion.
            checkpoint = {'status': 'partial-derived-checkpoint-not-a-complete-result',
                'records': sorted(records, key=lambda r: r['selection_id']), 'endpoint_occupancy': occupancy}
            write_json(output/'checkpoint.json', checkpoint)
            print(f'B1 morphology: {len(records)}/{len(selected)} windows; {pulse_records} pulse records', flush=True)
        del native, values
    del matrix
    return sorted(records, key=lambda r: r['selection_id']), occupancy


def cross_band_matches(records):
    result = []
    for left, right in itertools.combinations(records, 2):
        if not left['uses'] or not right['uses'] or left['event_window_s'] != right['event_window_s']:
            continue
        a0, a1 = left['band_indices']; b0, b1 = right['band_indices']
        for a, b in zip(left['residual_metrics']['scales'], right['residual_metrics']['scales']):
            pa = sorted(a['inside_pulses']+a['reference_pulses'], key=lambda p: p['peak_time_s'])
            pb = sorted(b['inside_pulses']+b['reference_pulses'], key=lambda p: p['peak_time_s'])
            result.append({'selection_pair': [left['selection_id'], right['selection_id']],
                'shared_native_channels': max(0, min(a1,b1)-max(a0,b0)),
                'requested_width_s': a['requested_width_s'], 'tolerance_s': a['effective_width_s'],
                'pulse_counts': [len(pa),len(pb)], 'matched_pulses': matched_pulses(pa,pb,a['effective_width_s'])})
    return result


def main():
    verify_manifest(ROOT/'LS4M_FREEZE.sha256')
    config = load('config/ls4m_control_morphology.json')
    for name, expected in config['input_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError('changed input: '+name)
    previous = load('results_ls4l_v2_vetoed_fragment_diagnostics/diagnostics.json.gz')
    previous_id = previous.pop('result_sha256')
    if hashlib.sha256(encoded(previous)).hexdigest() != previous_id or previous_id != config['ls4l_result_sha256']:
        raise ValueError('LS4L identity differs')
    selected = selections(previous)
    if len(selected) != 21 or sum(bool(s['uses']) for s in selected) != 17:
        raise ValueError('unexpected measured window inventory')
    source = config['source']
    if source['label'] != 'B1' or source not in load('config/ls4l_vetoed_fragment_diagnostics.json')['sources']:
        raise ValueError('only the original B1 HTR source is authorized')
    settings = load('config/ls4e_residual_qualification.json')['settings']
    old = load('config/ls4c_lhs1140_x_htr_followup.json')
    OUT.mkdir(exist_ok=False)
    write_json(OUT/'selection.json', {'selections': selected, 'ls4l_result_sha256': previous_id})
    rawdir = Path(tempfile.mkdtemp(prefix='setisearch-ls4m-', dir='/tmp'))
    receipt, charged, errors = None, 0, []
    try:
        path = rawdir/'B1.fil'
        for attempt in range(config['resource']['attempts_per_source']):
            charged += source['source_size_bytes']
            if charged > config['resource']['max_total_download_bytes']:
                raise ValueError('download budget exceeded')
            try:
                receipt = download_exact(source,path,config)
                break
            except Exception as exc:
                errors.append(str(exc))
                if attempt+1 == config['resource']['attempts_per_source']:
                    raise
        write_json(OUT/'source_receipt.json', {'label':'B1', **receipt,
            'charged_download_bytes':charged, 'attempt_errors':errors, 'raw_file_deleted':False})
        records, occupancy = analyse(path,source,old,selected,settings,config['resource'],OUT)
        replay = replay_checks(records,previous)
        result = {'status':'measured-control-morphology-complete', 'records':records,
            'endpoint_occupancy':occupancy, 'cross_band_matches':cross_band_matches(records),
            'replay':replay, 'ls4l_result_sha256':previous_id,
            'freeze_sha256':hashlib.sha256((ROOT/'LS4M_FREEZE.sha256').read_bytes()).hexdigest(),
            'source_sha256':source['source_sha256'], 'source_bytes_verified':receipt['bytes'],
            'original_stage1_vetoes_retained':True, 'acceptance_rules_changed':False,
            'sky_candidates_promoted':0, 'reserved_sources_opened':False, 'raw_arrays_published':False,
            'python_version':platform.python_version(), 'numpy_version':np.__version__}
        result['result_sha256'] = hashlib.sha256(encoded(result)).hexdigest()
        (OUT/'morphology.json.gz').write_bytes(gzip.compress(encoded(result),mtime=0))
        print(json.dumps({'status':result['status'], 'selections':len(records), 'replay':replay,
            'result_sha256':result['result_sha256']},indent=2),flush=True)
    except Exception as exc:
        write_json(OUT/'abort.json', {'status':'aborted-no-complete-conclusion', 'error':str(exc),
            'charged_download_bytes':charged, 'attempt_errors':errors})
        raise
    finally:
        shutil.rmtree(rawdir)
        if receipt is not None:
            write_json(OUT/'source_receipt.json', {'label':'B1', **receipt,
                'charged_download_bytes':charged, 'attempt_errors':errors, 'raw_file_deleted':True})


if __name__ == '__main__':
    main()
