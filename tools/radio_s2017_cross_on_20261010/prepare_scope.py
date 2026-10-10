#!/usr/bin/env python3
"""Metadata/opaque-byte-only preparation; root must invoke once after admission.

Never imports NumPy or opens NPZ/HDF5 contents. It pins the four completed source
families and their existing map contracts, plus root's actual durable/closed
admission. No scope should be generated until source review and root GO.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import time

FAMILY = 'radio_s2017_cross_on_20261010'
SCHEMA = 'SETI_S2017_SAVED_MAXIMA_MUTUAL_CROSS_ON_V1'
ONS = ('epoch1_on', 'epoch2_on', 'epoch3_on')
C0, COUNT, CORE = 179306496, 1048576, 4096
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
STEP = 8.0 / 784
Q128_SCOPE_SHA = 'a93d6dda3f813b84be2452928fe42be76b6de3cb96cf4f85c9beda47adc9ea86'
Q128_DRIVER_SHA = 'ca9c3890a8be325061e62c03b05aa795a582fc7d10012f0a565d8779920e6bf6'
BULK_DRIVER_SHA = '5ce9d5f861e06691183cf43fd4351bfe8a09b97763c3bd23add82ad338864554'
BULK_SCOPE_SHA = ['551083a9ba56bf960fa49e8868047f8016ba9a70a3a7b1df1a54333af8d56c9c',
    'd9b499662e8766058a74ac794225fd95a34d208a07f5a7e289ce306e8c957d68',
    '72c82c8fb36c26ce2f22d68d5e57a34e7c841ab7e0c83050f5b67e8f1459f759']
SOURCE_SHA = '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107'
Q128_FREEZE = 'e8ada3c888d1f07b33d25dccb9f7ddc0c7d23995'
BULK_FREEZE = '76fb1da5a0af22d6182daed90e4bdca92f2470f8'
Q128_QA_SHA = '2f70b95aec9237e5a7bec689e339980893ececee4bc8d9373cfdf636059b8b00'
BULK_QA_SHA = 'a1573fd36df4ee685cbafbaec429c0dd7b63efc9586e41825cbef3e2857340e3'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def pin(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path and path.is_file() and not path.is_symlink(), 'Canonical regular file required')
    return {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size}


def read_pinned(item):
    raw = Path(item['path']).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == item['sha256'] and len(raw) == item['bytes'], 'Pinned metadata snapshot differs')
    return json.loads(raw)


def save_new(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def metadata_contract(owner):
    qstage, bulk = owner / 'analysis/new_visit_recovery', owner / 'analysis/s2017_full_band'
    source_path = owner / 'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
    pinned, mapped, states = {}, {}, []
    def record(path, expected_sha=None):
        item = pin(path)
        require(expected_sha is None or item['sha256'] == expected_sha, 'Original source/code SHA differs')
        old = pinned.get(item['path'])
        require(old is None or old == item, 'Conflicting duplicate metadata pin')
        pinned[item['path']] = item
        return item
    def require_QA_pin(qa, item):
        path = Path(item['path'])
        keys = [str(path), str(path.relative_to(owner))]
        admitted = [qa['all_input_byte_pins'][key] for key in keys if key in qa['all_input_byte_pins']]
        require(len(admitted) == 1 and admitted[0] == {'sha256': item['sha256'], 'bytes': item['bytes']},
            'Fresh file bytes not attested by actual source QA')
    source_pin = record(source_path, SOURCE_SHA)
    source = read_pinned(source_pin)
    record(qstage / 'driver.py', Q128_DRIVER_SHA)
    record(bulk / 'driver.py', BULK_DRIVER_SHA)
    qscope_pin = record(qstage / 'scope.json', Q128_SCOPE_SHA)
    qqa_pin, bqa_pin = record(qstage / 'results/review/QA_RECEIPT.json'), record(bulk / 'results/review/QA_RECEIPT.json')
    qqa, bqa = read_pinned(qqa_pin), read_pinned(bqa_pin)
    require(qqa['status'] == 'PASS_THREE_S2017_MAPS_NINE_FIXED_PROFILES_AND111456_BITWISE_SOURCE_CELLS'
        and qqa['counts']['maps'] == 3 and bqa['status'] == 'PASS759_S2017_MAPS27_FIXED_PROFILES_AND334368_BITWISE_SOURCE_CELLS'
        and bqa['counts']['maps'] == 759, 'Actual complete QA receipts required')
    record(owner / 'analysis/new_visit_search/qa_saved_outputs.py', Q128_QA_SHA)
    record(bulk / 'qa_saved_outputs.py', BULK_QA_SHA)
    require(qqa['scope_sha256'] == Q128_SCOPE_SHA and qqa['driver_sha256'] == Q128_DRIVER_SHA
        and qqa['qa_script_sha256'] == Q128_QA_SHA and qqa['public_freeze_commit'] == Q128_FREEZE,
        'q128 QA scope/driver/script/freeze joins differ')
    require(bqa['driver_sha256'] == BULK_DRIVER_SHA and bqa['qa_script_sha256'] == BULK_QA_SHA
        and bqa['public_freeze_commit'] == BULK_FREEZE
        and bqa['scope_SHA256s'] == dict(zip(('batch01', 'batch02', 'batch03'), BULK_SCOPE_SHA)),
        'Bulk QA scope/driver/script/freeze joins differ')
    for relative, expected in [('analysis/new_visit_search/dependencies/detector.py', '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45'),
            ('analysis/new_visit_search/dependencies/gap_search.py', 'b1a2cc31d47dbebc707f36c5de3eafbae6a62f0d0d19061c798c676c9fbcdb58')]:
        record(owner / relative, expected)
    batches = [(None, [128], qstage / 'results/search', qscope_pin, qqa),
        ('batch01', list(range(1, 85)), bulk / 'results/batch01', record(bulk / 'scopes/batch01.json', BULK_SCOPE_SHA[0]), bqa),
        ('batch02', list(range(85, 128)) + list(range(129, 170)), bulk / 'results/batch02', record(bulk / 'scopes/batch02.json', BULK_SCOPE_SHA[1]), bqa),
        ('batch03', list(range(170, 255)), bulk / 'results/batch03', record(bulk / 'scopes/batch03.json', BULK_SCOPE_SHA[2]), bqa)]
    for batch, qs, directory, scope_pin, qa in batches:
        original_scope = read_pinned(scope_pin)
        if batch is not None:
            require(original_scope['core_q_indices'] == qs, 'Original 84/84/85 partition differs')
        terminal_pin = record(directory / 'EXECUTION_RECEIPT.json')
        terminal = read_pinned(terminal_pin)
        status = ('COMPLETE_NEW_S2017_THREE_CORE_MAPS_AND_NINE_FIXED_PROFILES_EXPLORATORY_ONLY' if batch is None
            else 'COMPLETE_S2017_PREVIOUSLY_UNSEARCHED_INTERIOR_BATCH_EXPLORATORY_ONLY')
        require(terminal['status'] == status and terminal['scope_sha256'] == scope_pin['sha256']
            and terminal['source_manifest_sha256'] == SOURCE_SHA
            and terminal['driver_sha256'] == (Q128_DRIVER_SHA if batch is None else BULK_DRIVER_SHA)
            and terminal['public_freeze_commit'] == (Q128_FREEZE if batch is None else BULK_FREEZE),
            'Original execution scope/source/driver/freeze differs')
        require((qqa['search_receipt_sha256'] if batch is None else bqa['search_receipt_SHA256s'][batch])
            == terminal_pin['sha256'], 'Actual QA does not bind admitted original execution')
        checkpoint_pin = record(directory / 'DRIFT_CHECKPOINT.json')
        require_QA_pin(qa, checkpoint_pin)
        checkpoint = read_pinned(checkpoint_pin)
        require(checkpoint['complete'] is True and checkpoint['completed_ON_maps'] == checkpoint['expected_ON_maps'] == 3 * len(qs)
            and len(checkpoint['receipts']) == 3 * len(qs), 'Original map checkpoint incomplete')
        seen = set()
        for item in checkpoint['receipts']:
            label, q = item['scan_id'], 128 if batch is None else item['core_q']
            require(label in ONS and q in qs and (label, q) not in seen and (label, q) not in mapped, 'Repeated/ineligible core')
            seen.add((label, q))
            expected_name = label + ('_core128_all_carriers.npz' if batch is None else '_q%03d_all_carriers.npz' % q)
            require(item['path'] == expected_name and item['searched_carriers'] == CORE
                and item['valid_hypotheses_per_carrier'] == 1570
                and item['reference_channel_interval_half_open'] == [C0 + q * CORE, C0 + (q + 1) * CORE], 'Original map identity/frame differs')
            mpin = pin(directory / item['path'])  # Opaque bytes only; no np.load.
            require(mpin['sha256'] == item['sha256'] and mpin['bytes'] == item['bytes'], 'Fresh map byte hash differs from checkpoint')
            require_QA_pin(qa, mpin)
            mapped[label, q] = {'scan_id': label, 'core_q': q, 'map_pin': mpin,
                'reference_channel_interval_half_open': item['reference_channel_interval_half_open'],
                'searched_carriers': CORE, 'valid_hypotheses_per_carrier': 1570,
                'original_checkpoint_pin': checkpoint_pin, 'original_execution_pin': terminal_pin,
                'normalization_kind': 'embedded_in_q128_checkpoint' if batch is None else 'separate_tile_normalization_JSON'}
            if batch is not None:
                normal = item['normalization']
                require(normal['path'] == label + '_q%03d_normalization.json' % q, 'Tile normalization path differs')
                npin = pin(directory / normal['path'])
                require(npin['sha256'] == normal['sha256'] and npin['bytes'] == normal['bytes'], 'Tile normalization byte pin differs')
                require_QA_pin(qa, npin)
                mapped[label, q]['normalization_pin'] = npin
        require(seen == {(label, q) for label in ONS for q in qs}, 'Original receipt grid incomplete')
        states.append({'batch_id': 'q128' if batch is None else batch, 'status': status,
            'scope_pin': scope_pin, 'execution_pin': terminal_pin, 'checkpoint_pin': checkpoint_pin})
    require(set(mapped) == {(label, q) for label in ONS for q in range(1, 255)}, 'All 762 maps required')
    require(set(bqa['search_receipt_SHA256s']) == {'batch01', 'batch02', 'batch03'}, 'Bulk QA terminal set differs')
    return source, source_pin, list(pinned.values()), [mapped[label, q] for label in ONS for q in range(1, 255)], states


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', required=True)
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--admission', required=True)
    parser.add_argument('--expected-admission-sha256', required=True)
    parser.add_argument('--root-go-metadata-only-after-durable-owner-checkpoints', action='store_true')
    args = parser.parse_args()
    cpu = time.process_time()
    require(args.root_go_metadata_only_after_durable_owner_checkpoints, 'Root metadata preparation GO required')
    project, owner = Path(args.project_root), Path(args.source_root)
    require(project.is_absolute() and owner.is_absolute() and project.resolve() == project and owner.resolve() == owner, 'Canonical roots required')
    tool = project / 'tools' / FAMILY
    scope_path = tool / 'scope.json'
    save_new(tool / 'SCOPE_PREPARATION_STARTED.json', {'status': 'STARTED_ONCE_METADATA_ONLY', 'family_id': FAMILY,
        'source_root': str(owner), 'admission_sha256': args.expected_admission_sha256})
    apin = pin(args.admission)
    require(apin['sha256'] == args.expected_admission_sha256, 'Admission SHA differs')
    admission = read_pinned(apin)
    require(admission['schema'] == 'SETI_S2017_CROSS_ON_ROOT_DURABLE_CLOSED_ADMISSION_V1'
        and admission['status'] == 'PASS_CLOSED_QA_DURABLE_RAW_AND_RESULTS_NO_DUPLICATE_MATCHER'
        and admission['source_root'] == str(owner) and admission['map_count'] == 762
        and all(admission[key] is True for key in ('all_numeric_and_QA_processes_closed', 'durable_RAW_verified',
            'durable_RESULTS_verified', 'fresh_registry_check_no_matching_duplicate', 'matching_not_previously_executed')), 'Actual admission is not ready')
    require({item['kind'] for item in admission['durability_proofs']} == {'RAW', 'RESULTS'}, 'Both durable proof classes required')
    for proof in admission['durability_proofs']:
        require(proof['verified'] is True and pin(proof['pin']['path']) == proof['pin'], 'Durable proof byte pin differs')
    source, source_pin, metadata, maps, states = metadata_contract(owner)
    originals = [item['execution_pin'] for item in states] + [item for item in metadata if item['path'].endswith('/review/QA_RECEIPT.json')]
    require(len(originals) == 6 and admission['original_execution_and_QA_pins'] == originals,
        'Admission must bind exact four execution and two QA receipts in fixed order')
    maps_sha = hashlib.sha256(json.dumps([item['map_pin'] for item in maps], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    require(admission['ordered_map_pins_sha256'] == maps_sha, 'Admission must already bind fresh ordered all-map pins')
    headers = {item['label']: item['current_header']['data_attributes'] for item in source['sources']}
    require(len(source['sources']) == len(headers) == 6, 'Six unique source headers required')
    anchor = min(float(header['tstart']) for header in headers.values())
    refs = [(float(headers[label]['tstart']) - anchor) * 86400 + .5 * TSAMP for label in ONS]
    for header in headers.values():
        require(float(header['fch1']) * 1e6 == FCH1 and float(header['foff']) * 1e6 == DF
            and float(header['tsamp']) == TSAMP, 'Original physical headers differ')
    # This pins the two separate IEEE float64 operations used by the original
    # NumPy linspace source: arange*step, then +start, then exact endpoint.
    # Runtime still requires each saved grid and winner to roundtrip bit-exactly.
    grid = [(-4.0 + (index * STEP)) for index in range(785)]
    grid[-1] = 4.0
    grid_sha = hashlib.sha256(struct.pack('<785d', *grid)).hexdigest()
    stage = project / 'results' / FAMILY
    stage.mkdir(exist_ok=True)
    own_metadata = [pin(tool / name) for name in ('prepare_scope.py', 'METHOD.md')]
    scope = {'schema': SCHEMA, 'family_id': FAMILY, 'status': 'PROSPECTIVE_NOT_EXECUTED',
        'user_authorization': 'Du kører bare på full power. Vi skal igennem en masse data for bare at have en lille chance for success.',
        'script_path': str(tool / 'match_saved.py'), 'script_sha256': sha(tool / 'match_saved.py'),
        'source_root': str(owner), 'source_manifest_pin': source_pin, 'admission_pin': apin,
        'pinned_metadata_files': metadata + own_metadata, 'original_families': states, 'maps': maps,
        'original_execution_and_QA_pins': originals,
        'ordered_map_pins_sha256': maps_sha, 'scan_order': list(ONS), 'source_channel0': C0,
        'native_chunk_count_channels': COUNT, 'core_channel_count': CORE, 'core_q_indices': list(range(1, 255)),
        'map_count': 762, 'records_per_ON': 254 * CORE, 'carrier_maximum_records': 3 * 254 * CORE,
        'excluded_edge_q': [0, 255], 'fch1_hz': FCH1, 'df_hz': DF, 'tsamp_s': TSAMP,
        'MJD_anchor': anchor, 'ON_reference_seconds_from_anchor': refs,
        'common_reference_seconds_from_anchor': .5 * (refs[0] + refs[2]),
        'common_reference_MJD_display_only': anchor + .5 * (refs[0] + refs[2]) / 86400,
        'reference_rule': 'midpoint of ON1 and ON3 first integration midpoint references',
        'transport_formula': 'fstar=FCH1+DF*absolute_source_channel+saved_drift*(common_ref_seconds-original_ON_ref_seconds)',
        'frequency_tolerance_rule': '3*abs(df)+0.5*(8/784)*(t_ON3-t_ON1)',
        'frequency_tolerance_hz': 3 * abs(DF) + .5 * STEP * (refs[2] - refs[0]),
        'grid_creation_expression': 'numpy 2.3.5: np.linspace(-4.0, 4.0, 785, dtype=np.float64)',
        'grid_float64_le_sha256': grid_sha, 'grid_count': 785, 'grid_step_hz_s': STEP, 'drift_index_tolerance': 1,
        'widths_channels': [1, 3], 'width_rule': 'retain each original winner width; equal widths not required',
        'nearest_lexicographic_rule': ['absolute_frequency_gap', 'absolute_drift_index_gap', 'target_absolute_source_channel'],
        'mutual_rule': 'all six directed nearest links must agree on the same triple, then max-min frequency<=tau and max-min drift_index<=1',
        'maximum_candidates_per_record_per_directed_match': 6,
        'triple_ranking_rule': ['minimum_of_three_saved_scores_descending', 'ON1_channel', 'ON2_channel', 'ON3_channel'],
        'top_count': 1000, 'relation_columns': list(ONS), 'relation_dtype': '<i4',
        'relation_index_domain': 'zero-based increasing absolute source channels q1..254 per ON',
        'CPU_cap_s': 120.0, 'wall_cap_s': 1800.0, 'memory_cap_bytes': 1073741824,
        'output_reservation_bytes': 67108864, 'shared_workspace_cap_bytes': 8589934592,
        'shared_workspace_roots': admission['shared_workspace_roots'], 'output_directory': str(stage / 'measurement'),
        'owner_scientific_command_paths': ['analysis/new_visit_recovery/driver.py',
            'analysis/s2017_full_band/driver.py', 'analysis/new_visit_search/qa_saved_outputs.py',
            'analysis/s2017_full_band/qa_saved_outputs.py'],
        'owner_kernel_guard_paths': [str(owner / name) for name in [
            'analysis/new_visit_recovery/results/ACTIVE_FAMILY_FLOCK.lock',
            'analysis/s2017_full_band/results/ACTIVE_SCIENCE_SLOT_0_FLOCK.lock',
            'analysis/s2017_full_band/results/ACTIVE_SCIENCE_SLOT_1_FLOCK.lock',
            'analysis/s2017_full_band/results/REVIEW_ACTIVE_FLOCK.lock',
            'analysis/s2017_full_band/results/batch01_ACTIVE_FLOCK.lock',
            'analysis/s2017_full_band/results/batch02_ACTIVE_FLOCK.lock',
            'analysis/s2017_full_band/results/batch03_ACTIVE_FLOCK.lock']],
        'attempt_marker_path': str(stage / 'MATCH_STARTED_ONCE.json'), 'serial_gate_path': str(stage / 'SERIAL_ACTIVE.flock'),
        'runtime_numpy': '2.3.5', 'new_source_BODY_bytes': 0, 'new_HTTP_requests': 0, 'cost_DKK': 0,
        'retry_resume_or_rerun_authorized': False, 'profile_measurement_authorized': False,
        'OFF_veto_applied': False, 'independent_validation_claimed': False,
        'blind_selection_before_fresh_values': False, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED',
        'note': 'New posthoc association family; original q128 and bulk execution and QA statuses remain unchanged.'}
    # Final metadata and opaque input byte readback; no observation arrays open.
    for item in scope['pinned_metadata_files'] + [apin]:
        require(pin(item['path']) == item, 'Preparation metadata changed')
    for proof in admission['durability_proofs']:
        require(pin(proof['pin']['path']) == proof['pin'], 'Durability proof changed during preparation')
    require(sha(tool / 'match_saved.py') == scope['script_sha256'], 'Matcher source changed during preparation')
    for item in maps:
        require(pin(item['map_pin']['path']) == item['map_pin'], 'Map changed during opaque preparation')
        if 'normalization_pin' in item:
            require(pin(item['normalization_pin']['path']) == item['normalization_pin'], 'Normalization bytes changed')
    save_new(scope_path, scope)
    save_new(tool / 'SCOPE_PREPARATION_RECEIPT.json', {'status': 'COMPLETE_METADATA_ONLY_SCOPE_PREPARATION',
        'family_id': FAMILY, 'scope_pin': pin(scope_path), 'script_sha256': scope['script_sha256'],
        'maps_pinned': 762, 'separate_normalization_files_pinned': 759, 'q128_embedded_normalization_records': 3,
        'scientific_arrays_opened': False, 'matcher_executed': False, 'process_CPU_seconds': time.process_time() - cpu})
    print(json.dumps({'scope_sha256': sha(scope_path), 'maps_pinned': 762, 'process_CPU_seconds': time.process_time() - cpu}))


if __name__ == '__main__':
    main()
