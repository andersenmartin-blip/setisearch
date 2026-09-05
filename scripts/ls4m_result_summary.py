#!/usr/bin/env python3
"""Verify retained LS4M evidence and summarize exact denominators without raw data."""
import hashlib
import json
from pathlib import Path

import numpy as np

from ls4m_control_morphology import (ROOT, OUT, load, encoded, write_json, replay_checks,
    cross_band_matches, peak_sample_bounds)
from ls4g_synthetic_recovery import verify_manifest


def interval(values):
    return [min(values),max(values)] if values else None


def main():
    verify_manifest(ROOT/'LS4M_FREEZE.sha256')
    result = load('results_ls4m_control_morphology/morphology.json.gz')
    identity = result.pop('result_sha256')
    if hashlib.sha256(encoded(result)).hexdigest() != identity:
        raise ValueError('result identity mismatch')
    config = load('config/ls4m_control_morphology.json')
    for name, expected in config['input_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError('changed frozen input: '+name)
    previous = load('results_ls4l_v2_vetoed_fragment_diagnostics/diagnostics.json.gz')
    source = load('results_ls4m_control_morphology/source_receipt.json')
    if (result['status'] != 'measured-control-morphology-complete' or
        source['source_sha256'] != config['source']['source_sha256'] or
        source['bytes'] != config['source']['source_size_bytes'] or not source['raw_file_deleted'] or
        result['source_sha256'] != source['source_sha256'] or result['source_bytes_verified'] != source['bytes'] or
        source['charged_download_bytes'] > config['resource']['max_total_download_bytes'] or
        result['sky_candidates_promoted'] or result['reserved_sources_opened'] or
        result['acceptance_rules_changed'] or not result['original_stage1_vetoes_retained']):
        raise ValueError('source or scientific boundary mismatch')
    checkpoint = load('results_ls4m_control_morphology/checkpoint.json')
    if checkpoint['records'] != result['records'] or checkpoint['endpoint_occupancy'] != result['endpoint_occupancy']:
        raise ValueError('final derived checkpoint differs')
    if replay_checks(result['records'],previous) != result['replay']:
        raise ValueError('replay annotation mismatch')
    if cross_band_matches(result['records']) != result['cross_band_matches']:
        raise ValueError('cross-band annotation mismatch')
    settings = load('config/ls4e_residual_qualification.json')['settings']
    header = load('config/ls4c_lhs1140_x_htr_followup.json')['expected_filterbank_header']
    if result['freeze_sha256'] != hashlib.sha256((ROOT/'LS4M_FREEZE.sha256').read_bytes()).hexdigest():
        raise ValueError('freeze identity differs')
    if result['ls4l_result_sha256'] != config['ls4l_result_sha256']:
        raise ValueError('parent identity differs')
    widths = settings['pulse_width_s']
    for record in result['records']:
        metrics = record['residual_metrics']; band = record['band_indices']
        if (metrics['sample_count'] != header['ntime'] or metrics['sample_time_s'] != header['tsamp_s'] or
            [s['requested_width_s'] for s in metrics['scales']] != widths):
            raise ValueError('measurement geometry differs')
        for scale in metrics['scales']:
            for region in ('inside_pulses','reference_pulses'):
                for pulse in scale[region]:
                    descriptor = pulse['peak_channel_excess']
                    excess = np.array(descriptor['positive_excess_counts_by_channel'])
                    if len(excess) != band[1]-band[0] or np.any(excess < 0) or not np.isfinite(excess).all():
                        raise ValueError('invalid channel excess')
                    total = float(excess.sum())
                    fraction = float(excess.max()/total) if total else None
                    effective = float(total**2/(excess**2).sum()) if total else None
                    if (fraction != descriptor['largest_channel_fraction'] or effective != descriptor['effective_positive_channels'] or
                        np.count_nonzero(excess) != descriptor['positive_channel_count']):
                        raise ValueError('concentration annotation differs')
                    lo,hi = peak_sample_bounds(pulse['peak_time_s'],scale['effective_width_s'],header['tsamp_s'],header['ntime'])
                    if descriptor['peak_sample_count'] != hi-lo:
                        raise ValueError('pulse block annotation differs')
    rows=[]
    for category in ('selected','fixed'):
        for fi in range(2):
            records=[r for r in result['records'] if r['frequency_index']==fi and bool(r['uses'] if category=='selected' else r['fixed_uses'])]
            for si,width in enumerate(widths):
                scales=[r['residual_metrics']['scales'][si] for r in records]
                inside=[p for s in scales for p in s['inside_pulses']]
                reference=[p for s in scales for p in s['reference_pulses']]
                pulses=inside+reference
                fractions=[p['peak_channel_excess']['largest_channel_fraction'] for p in pulses if p['peak_channel_excess']['largest_channel_fraction'] is not None]
                effective=[p['peak_channel_excess']['effective_positive_channels'] for p in pulses if p['peak_channel_excess']['effective_positive_channels'] is not None]
                rows.append({'category':category,'band_ghz':[8.5,10.5][fi],'width_s':width,
                    'unique_windows':len(records),'inside_pulse_records':len(inside),'reference_pulse_records':len(reference),
                    'inside_peak_time_range_s':interval([p['peak_time_s'] for p in inside]),
                    'reference_peak_time_range_s':interval([p['peak_time_s'] for p in reference]),
                    'peak_score_range':interval([p['peak_score'] for p in pulses]),
                    'largest_channel_fraction_range':interval(fractions),
                    'largest_channel_fraction_median':float(np.median(fractions)) if fractions else None,
                    'effective_positive_channels_range':interval(effective)})
    bands=[]
    for fi in range(2):
        records=[r for r in result['records'] if r['frequency_index']==fi and r['uses']]
        allp=[p for r in records for s in r['residual_metrics']['scales'] for region in ('inside_pulses','reference_pulses') for p in s[region]]
        bands.append({'band_ghz':[8.5,10.5][fi],'unique_selected_windows':len(records),
            'off_veto_windows':sum(any(s['inside_pulses'] or s['reference_pulses'] for s in r['residual_metrics']['scales']) for r in records),
            'windows_with_inside_pulses':sum(any(s['inside_pulses'] for s in r['residual_metrics']['scales']) for r in records),
            'windows_with_reference_pulses':sum(any(s['reference_pulses'] for s in r['residual_metrics']['scales']) for r in records),
            'reused_fragment_evaluations':sum(len(r['uses']) for r in records),
            'pulse_records_across_scales':len(allp), 'peak_time_range_s':interval([p['peak_time_s'] for p in allp])})
    summary={'status':result['status'],'result_sha256':identity,'bands':bands,'scale_rows':rows,
        'selected_fragment_replay_uses':result['replay']['selected_fragment_evaluations'],
        'fixed_window_replay_uses':result['replay']['fixed_window_evaluations'],
        'source_bytes_verified':source['bytes'],'charged_download_bytes':source['charged_download_bytes'],
        'original_stage1_vetoes_retained':True,'acceptance_rules_changed':False,'sky_candidates_promoted':0}
    write_json(OUT/'summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='scale_rows'},indent=2))


if __name__=='__main__': main()
