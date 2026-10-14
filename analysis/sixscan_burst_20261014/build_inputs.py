#!/usr/bin/env python3
"""Write prospective six-scan definitions using authenticated JSON metadata only."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path

NAMESPACE = 'SETI_SIXSCAN_BURST_20261014'
SUBSETS = ((0,), (2,), (4,), (0, 2), (0, 4), (2, 4), (0, 2, 4))
SOURCE_JSON = 'seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json'
SOURCE_JSON_SHA = '31efe1e5eeba63d10fbc04ea60bd29eb3086f142b6111a185f821a40a0558522'
SOURCE_ARCHIVE_SHA = '52b948958c89069a7afb563cf377ee33e4f1324e014428d597b4b3e3a20f6eb3'
SCAN_IDS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
CORE = (179531776, 179535872)
LOADED = (179527776, 179539872)
WIDTHS = (1, 3, 9, 33)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def dump_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def placement(serial):
    return (.25, 4094.75, 1024.25, 3070.75)[serial % 4]


def definition(family, serial, active=(), drift=None, intrinsic=None, level=0., offset=None):
    identity = f'{NAMESPACE}:{family}:{serial:03d}'
    layers = []
    for index in active:
        start = (0, 6, 12)[(serial + index) % 3]
        rows = [6] if family == 'single_row_transient' else list(range(start, start + 4))
        window = list(range(6, 10)) if family == 'single_row_transient' else list(range(start, start + 4))
        layers.append({'scan_index': index, 'kind': 'PRIMARY', 'active_source_rows': rows,
                       'truth_window_source_rows': window, 'drift_hz_s': drift,
                       'intrinsic_width_channels': intrinsic, 'nominal_ideal_box_score': level,
                       'reference_native_offset': offset})
    return {'case_id': identity, 'family': family, 'serial': serial,
            'seed_sha256': sha_bytes(identity.encode('ascii')), 'noise_law': 'gamma16',
            'active_scan_indices': list(active), 'drift_hz_s': drift,
            'intrinsic_width_channels': intrinsic, 'nominal_ideal_box_score': level,
            'reference_native_offset': offset, 'signal_layers': layers,
            'eligibility_case': family in ('strong', 'operating', 'matched_rfi', 'null'),
            'calibration_reference': family == 'calibration',
            'diagnostic_only': family in ('single_row_transient', 'near_off_contamination')}


def cases():
    bank = [definition('calibration', serial) for serial in range(63)]
    for serial, (active, drift) in enumerate(itertools.product(SUBSETS, (-4., 4.))):
        bank.append(definition('strong', serial, active, drift, 1 if serial % 2 == 0 else 3,
                               32., placement(serial)))
    for serial, (active, drift, intrinsic) in enumerate(itertools.product(SUBSETS[:6], (-4., -1.25, 1.25, 4.), (1, 3))):
        bank.append(definition('operating', serial, active, drift, intrinsic, 16., placement(serial)))
    for serial, (drift, intrinsic, level, offset) in enumerate(itertools.product((-4., 0., 4.), (1, 3), (16., 32.), (1024.25, 3070.75))):
        bank.append(definition('matched_rfi', serial, range(6), drift, intrinsic, level, offset))
    bank.extend(definition('null', serial) for serial in range(32))
    for serial, (index, drift) in enumerate(itertools.product(range(6), (-4., 4.))):
        bank.append(definition('single_row_transient', serial, (index,), drift,
                               1 if serial % 2 == 0 else 3, 32., placement(serial)))
    for serial, (index, drift, off_offset) in enumerate(itertools.product((0, 2, 4), (-1.25, 1.25), (3., 64.))):
        item = definition('near_off_contamination', serial, (index,), drift,
                          1 if serial % 2 == 0 else 3, 32., placement(serial))
        off_index = index + 1
        start = (0, 6, 12)[(serial + off_index) % 3]
        item['diagnostic_off_frequency_offset_channels'] = off_offset
        item['signal_layers'].append({'scan_index': off_index, 'kind': 'NEAR_OFF_NUISANCE',
            'active_source_rows': list(range(start, start + 4)),
            'truth_window_source_rows': list(range(start, start + 4)), 'drift_hz_s': drift,
            'intrinsic_width_channels': item['intrinsic_width_channels'],
            'nominal_ideal_box_score': 32., 'reference_native_offset': item['reference_native_offset'] + off_offset})
        bank.append(item)
    expected = {'calibration': 63, 'strong': 14, 'operating': 48, 'matched_rfi': 24,
                'null': 32, 'single_row_transient': 12, 'near_off_contamination': 12}
    if Counter(item['family'] for item in bank) != expected or len(bank) != 205:
        raise ValueError('Fixed prospective bank dimensions differ')
    if len({item['case_id'] for item in bank}) != 205 or len({item['seed_sha256'] for item in bank}) != 205:
        raise ValueError('Duplicate prospective identity')
    return bank


def build(input_root, output):
    matrix_path = Path(input_root) / SOURCE_JSON
    raw = matrix_path.read_bytes()
    if len(raw) != 629588 or sha_bytes(raw) != SOURCE_JSON_SHA:
        raise ValueError('Authenticated source JSON identity differs')
    matrix = json.loads(raw)
    compacts = matrix['source_compacts']
    scans = []
    for scan_id in SCAN_IDS:
        matches = [c for c in compacts if c['scan_id'] == scan_id and c['native_chunk_index'] == 170]
        if len(matches) != 1:
            raise ValueError('Exactly one native170 header per scan required')
        full = matches[0]['original_header_full']
        h = full['data_attributes']
        if full['dataset_shape'][:2] != [16, 1] or h != matches[0]['original_header']:
            raise ValueError('Full and scalar source headers differ')
        for duplicate in (c for c in compacts if c['scan_id'] == scan_id):
            if duplicate['original_header_full'] != full:
                raise ValueError('Header geometry changes across native chunks')
        scans.append({'scan_id': scan_id, 'role': 'ON' if scan_id.endswith('_on') else 'OFF',
                      'nrows': 16, 'tstart_mjd': float(h['tstart']), 'tsamp_s': float(h['tsamp']),
                      'fch1_hz': float(h['fch1']) * 1e6, 'df_hz': float(h['foff']) * 1e6,
                      'original_header_full': full})
    anchor = min(s['tstart_mjd'] for s in scans)
    all_times = []
    end = -math.inf
    for scan in scans:
        start = (scan['tstart_mjd'] - anchor) * 86400.
        if start < end:
            raise ValueError('Source scans overlap or are not chronological')
        end = start + scan['nrows'] * scan['tsamp_s']
        times = [start + (row + .5) * scan['tsamp_s'] for row in range(16)]
        all_times.extend(times)
        scan['row_midpoints_seconds_from_anchor'] = times
    tref = .5 * (all_times[0] + all_times[-1])
    for scan in scans:
        scan['row_midpoints_seconds_from_tref'] = [t - tref for t in scan['row_midpoints_seconds_from_anchor']]
    df = min(abs(s['df_hz']) for s in scans)
    span = all_times[-1] - all_times[0]
    half_steps = math.ceil(4. * span / df)
    contract = {'schema': 'SETI_SIXSCAN_BURST_CONTRACT_V1', 'status': 'PROSPECTIVE_METADATA_ONLY_REQUIRES_ROOT_GO',
        'study_id': NAMESPACE, 'source_metadata_pin': {'path': SOURCE_JSON, 'bytes': len(raw), 'sha256': SOURCE_JSON_SHA},
        'source_archive_pin': {'name': 'SETI_NATIVE_SPOR_2026-10-14.zip', 'sha256': SOURCE_ARCHIVE_SHA,
                               'archive_payload_opened_by_builder': False},
        'geometry': {'reference_source_channel_interval': list(CORE), 'loaded_source_channel_interval': list(LOADED),
                     'first_scan_start_mjd': anchor, 'tref_relative_first_scan_start_s': tref,
                     'tref_mjd': anchor + tref / 86400., 'scan_metadata': scans,
                     'source_rows_per_scan': 16, 'window_start_rows': [0, 2, 4, 6, 8, 10, 12],
                     'window_length_rows': 4, 'injection_window_start_choices': [0, 6, 12],
                     'injection_window_choice': 'choices[(case serial + original scan index) % 3]',
                     'single_row_diagnostic': {'active_row': 6, 'truth_window_rows': [6, 7, 8, 9], 'score_normalization_rows': 4},
                     'global_drift_grid': {'maximum_abs_hz_s': 4., 'count': 2 * half_steps + 1,
                                           'step_hz_s': 8. / (2 * half_steps),
                                           'construction': 'n=ceil(4*fullsixscan-midpoint-span/minabsdf); linspace(-4,4,2n+1); exact center zero',
                                           'full_midpoint_span_s': span}},
        'background': {'law': 'independent_gamma16', 'mean': 1., 'sigma': .25, 'shape': 16., 'scale': .0625,
                       'independent_scans_rows_channels': True, 'generator': 'NumPy Generator(PCG64(int(full SHA256 ASCII case identity,16)))',
                       'dtype_pipeline': 'gamma float64 + all float64 signal layers, then one float32 cast per complete scan',
                       'numpy_version': '2.3.5', 'positivity': 'finite positive source; no clipping, retries or redraws'},
        'signal': {'kernel': 'unit-area intrinsic U[-a/2,a/2] convolved with uniform exposure sweep abs(d)*tsamp/abs(df)',
                   'channel_weight': 'CDF(j+.5-continuouscenter)-CDF(j-.5-continuouscenter)',
                   'continuouscenter': 'corefirst+offset+d*(actual row midpoint-globaltref)/signeddf; float64 before rounding',
                   'rounding': 'numpy.rint complete absolute source channel; nearest ties to even',
                   'oracle_widths': list(WIDTHS), 'oracle_denominator': 'sqrt(4*width) including single-row diagnostics',
                   'flux': '.25*nominal_ideal_box_score / max_width(sum(unit kernel mass in true nearest-center box on injected rows)/sqrt(4width))',
                   'oracle_before_RNG': True, 'no_observed_values_in_oracle': True,
                   'amplitude_is_nominal_noise_free_projection_not_SNR_or_flux_calibration': True},
        'selection': {'widths': list(WIDTHS), 'combined_retained_candidates': 5, 'ON_threshold': 10., 'OFF_threshold': 8.,
                      'calibration_references': 63, 'calibration_statistic': 'global maximum over complete declared ON search family before OFF',
                      'final_candidate_p': '(1 + count63(referenceglobalONmax >= candidate score))/64',
                      'final_candidate_p_cut_inclusive': 1. / 64., 'calibration_law_only': 'independent_gamma16',
                      'physical_or_telescope_FAP_calibrated': False},
        'joint_gate': {'all_205_integrity_required': True, 'strong_all': 14, 'operating_at_least': 44,
                      'operating_each_activity_at_least': 7, 'operating_each_drift_at_least': 10,
                      'operating_each_intrinsic_width_at_least': 22, 'matched_RFI_all_pre_OFF_localized': 24,
                      'matched_RFI_maximum_surviving_cadences': 0, 'null_maximum_surviving_cadences': 1,
                      'null_case_count': 32, 'diagnostics_complete': 24},
        'preserved': {'original_A_B': 'FAIL_CLOSED', 'protected_2016': True, 'closed_2019': True,
                      'new_telescope_requests': 0, 'new_telescope_bytes': 0, 'new_observation': False,
                      'qualified_SETI_detection': False},
        'builder_does_not_import_NumPy_generate_RNG_or_open_arrays': True}
    real = []
    groups = sorted({(c['native_chunk_index'], c['core_q']) for c in matrix['normalization_crops']})
    if len(groups) != 9:
        raise ValueError('Nine authentic exposed cadence bands required')
    for native, q in groups:
        members = [c for c in matrix['normalization_crops'] if (c['native_chunk_index'], c['core_q']) == (native, q)]
        by_id = {c['scan_id']: c for c in members}
        if set(by_id) != set(SCAN_IDS) or len(members) != 6:
            raise ValueError('Authentic cadence does not contain exactly six scans')
        ordered = [by_id[s] for s in SCAN_IDS]
        first = ordered[0]['normalization_source_channel_interval_half_open']
        loaded = ordered[0]['source_channel_interval_half_open']
        if first[1] - first[0] != 4096 or loaded[1] - loaded[0] != 12096:
            raise ValueError('Authentic crop dimensions differ')
        if any(c['normalization_source_channel_interval_half_open'] != first or c['source_channel_interval_half_open'] != loaded for c in ordered):
            raise ValueError('Authentic same-band channel coordinates differ across scans')
        real.append({'case_id': f'{NAMESPACE}:real_sham:native{native}_q{q:03d}', 'family': 'real_sham',
            'diagnostic_only': True, 'fresh_background': False, 'synthetic_injection': False,
            'native_chunk_index': native, 'core_q': q, 'reference_source_channel_interval': first,
            'loaded_source_channel_interval': loaded, 'source_rows_per_scan': 16,
            'scans': [{'scan_id': c['scan_id'], 'raw_crop': {**c['raw_crop'], 'path': 'seti_work/' + c['raw_crop']['path']},
                       'normalization': {**c['normalization'], 'path': 'seti_work/' + c['normalization']['path']}} for c in ordered],
            'interpretation': 'Exposed 2017 background diagnostic; neither independent null nor new observation; no synthetic Gamma16 FAP transfer.'})
    bank = cases()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    payloads = {'contract.json': contract, 'case_bank.json': bank, 'real_baselines.json': real}
    for name, value in payloads.items():
        dump_new(output / name, value)
    receipt = {'schema': 'SETI_SIXSCAN_INPUT_METADATA_RECEIPT_V1', 'status': 'COMPLETE_METADATA_ONLY',
        'source_json_pin': contract['source_metadata_pin'], 'case_count': len(bank),
        'family_counts': dict(Counter(c['family'] for c in bank)), 'real_sham_cadences': len(real),
        'raw_array_or_score_payloads_opened': False, 'RNG_instantiated': False,
        'outputs': [{'path': name, 'bytes': (output / name).stat().st_size,
                     'sha256': sha_bytes((output / name).read_bytes())} for name in payloads]}
    dump_new(output / 'INPUT_METADATA_RECEIPT.json', receipt)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Write metadata only; never create noise or spectral arrays')
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.input_root, args.output), indent=2, sort_keys=True))
