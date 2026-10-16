#!/usr/bin/env python3
"""Independent complete-search QA for one fresh deterministic engineering case.

No numerical package is imported at module import. This verifier imports only
the unchanged legacy QA functions and the separately pinned payload adapter.
It does not import a producer's fixture arithmetic, detector, generator, old
study main, admission routine, random API, bank, or observation checkpoint.
The caller must freeze this source and reserve/guard the whole process first.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import sys
import time


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1]
LEGACY = SOURCE / 'analysis/sixscan_burst_20261015'
TRANSPORT = SOURCE / 'tools/science_payload_20261016/payload.py'
IDENTITY = 'SETI_FULLSEARCH_PAYLOAD_ENGINEERING_20261016_V1'
MODE = 'ENGINEERING_FIXTURES_ONLY'
SCHEMA = 'SETI_COMPLETE_SEARCH_PAYLOAD_ENGINEERING_QA_V1'
PAYLOAD_CAP = 768 * 1024**2
REPORT_CAP = 2 * 1024**2
RAW_EXPANSION_CAP = 800 * 1024**2
LOG_CAP = 64 * 1024
STARTED = time.monotonic()
PROGRESS = {'stage': 'BEFORE_PREFLIGHT', 'full_search_checks': []}


class BoundedText:
    """Bound Python output; native descriptor output remains a parent gate."""
    def __init__(self, stream):
        self.stream, self.remaining, self.overflow = stream, LOG_CAP, False

    def write(self, text):
        text = str(text)
        raw = text.encode('utf-8', errors='replace')
        kept = raw[:self.remaining]
        self.remaining -= len(kept)
        self.overflow |= len(kept) != len(raw)
        self.stream.write(kept.decode('utf-8', errors='ignore'))
        return len(text)

    def flush(self):
        self.stream.flush()

    def isatty(self):
        return False


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(type(key) is str and key not in result, 'Duplicate or nonstring receipt key')
        result[key] = value
    return result


def read(path, cap=2 * 1024**2):
    path = Path(path)
    require(not path.is_symlink() and path.is_file() and path.stat().st_size <= cap,
            'Bounded regular engineering receipt required')
    return json.loads(path.read_text(), object_pairs_hook=_pairs)


def save(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    require(len(raw) <= REPORT_CAP, 'Independent QA report exceeds its physical cap')
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def independent_raw(np, scan_index):
    """2D coordinate implementation of the frozen integer counter arithmetic.

    The constants define a deterministic value map, with modulo-2**64
    unsigned arithmetic and20 retained counter bits. There is no RNG state,
    draw, seed API, probability model, or noise/calibration-law assertion.
    The producer's numerical helper is never imported or called.
    """
    row = np.arange(16, dtype=np.uint64).reshape(16, 1)
    column = np.arange(12096, dtype=np.uint64).reshape(1, 12096)
    salt = np.uint64(((scan_index + 1) * 0x9E3779B97F4A7C15) & ((1 << 64) - 1))
    counter = row * np.uint64(12096) + column + salt
    mixed = (counter ^ np.right_shift(counter, np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    mixed = (mixed ^ np.right_shift(mixed, np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    mixed ^= np.right_shift(mixed, np.uint64(31))
    low_bits = np.bitwise_and(mixed, np.uint64(1048575))
    result = (0.75 + low_bits.astype(np.float64) / 2097152.0).astype('<f4')
    # Fixed physical fixture locations, not inferred from observed maps/hits.
    if scan_index in (0, 1):
        result[6:10, 5024] += np.float32(2.0)
    if scan_index == 2:
        result[6:10, 7072] += np.float32(2.0)
    return result


class WorkerArrayStore:
    def __init__(self, archive):
        self.archive = archive

    def __getitem__(self, key):
        return self.archive.load(('worker_arrays', key))


def _descriptor_inventory(encoded, descriptors, audit):
    found = {}
    fields = {'npz_key', 'shape', 'dtype', 'C_order_bytes_sha256', 'nbytes', 'original_field_path'}

    def visit(value, path=()):
        if type(value) is dict and set(value) == {'array_descriptor'}:
            descriptor = value['array_descriptor']
            require(type(descriptor) is dict and set(descriptor) == fields,
                    'Complete original legacy descriptor fields required')
            key = descriptor['npz_key']
            require(type(key) is str and key not in found, 'Duplicate legacy array reference')
            audit.eq(descriptor['original_field_path'], list(path), 'Original complete numerical field path')
            found[key] = descriptor
        elif type(value) is dict:
            for key, child in value.items():
                visit(child, path + (str(key),))
        elif type(value) is list:
            for i, child in enumerate(value):
                visit(child, path + (str(i),))

    visit(encoded)
    audit.eq(found, descriptors, 'Original full descriptor inventory and order')
    audit.eq(list(found), list(descriptors), 'Original ordered legacy descriptor-key inventory')
    #14 numerical fields per scan;9 per OFF inventory;7 geometry fields;
    #4 per each of6 x7window x2parity complete alias tables.
    audit.eq(len(found), 6 * 14 + 3 * 9 + 7 + 6 * 7 * 2 * 4,
             'Complete actual legacy numerical-array census without list coercion')
    return found


def _check_truth(truth, active_id, reference, input_hashes, audit):
    audit.eq(type(truth).__name__, 'dict', 'Original truth remains a dict')
    audit.eq(type(truth['active_ON_scan_ids']).__name__, 'list', 'Original activity remains a list')
    audit.eq(truth['case_id'], IDENTITY, 'Independent engineering truth identity')
    audit.eq(truth['active_ON_scan_ids'], [active_id], 'Independent prescribed activity')
    audit.eq(truth['reference_source_channel_at_tref'], reference, 'Independent prescribed source carrier')
    audit.eq(truth['drift_hz_s'], 0., 'Independent prescribed stationary reference drift')
    audit.eq(truth['active_window_start_by_scan'], {active_id: 6}, 'Independent prescribed four-row activity window')
    audit.eq(truth['oracle_width_by_scan'], {active_id: 1}, 'Independent prescribed nominal fixture width')
    audit.eq(truth['authenticated_input_arrays'], input_hashes, 'All truth-authenticated complete raw arrays')
    for key, expected_type in (('case_id', str), ('active_ON_scan_ids', list),
            ('reference_source_channel', int), ('reference_source_channel_at_tref', int),
            ('drift_hz_s', float), ('active_window_start_by_scan', dict), ('oracle_width_by_scan', dict),
            ('authenticated_input_arrays', dict), ('scientific_admission', bool), ('RNG_called', bool)):
        audit.eq(type(truth[key]).__name__, expected_type.__name__, 'Exact original truth field type ' + key)


def _authenticate_scope_and_guard(folder, producer):
    """Read/hash only; independent preflight before importing NumPy/payload."""
    scope_path = folder.parent / 'FROZEN_SCOPE.json'
    scope = read(scope_path)
    require(sha(scope_path) == producer['scope_sha256'], 'Exact producer-frozen scope bytes differ')
    require(scope['schema'] == 'SETI_COMPLETE_SEARCH_ENGINEERING_SCOPE_V1' and
            scope['identity'] == IDENTITY and scope['mode'] == MODE and
            Path(scope['output_root']).resolve() == folder.parent.resolve(),
            'New namespace complete-search engineering scope required')
    pins = scope['source_pins']
    require(type(pins) is list and pins, 'Complete source freeze required')
    observed = {}
    for pin in pins:
        relative = Path(pin['path'])
        require(not relative.is_absolute() and '..' not in relative.parts,
                'Frozen source pin must be a safe relative path')
        path = (SOURCE / relative).resolve()
        require(SOURCE in path.parents and pin['path'] not in observed,
                'Duplicate or outside frozen source pin')
        require(path.stat().st_size == pin['bytes'] and sha(path) == pin['sha256'],
                'Complete frozen source bytes differ before independent numerical imports')
        observed[pin['path']] = {'bytes': pin['bytes'], 'sha256': pin['sha256']}
    required = {'tools/fullsearch_integration_20261016/verifier.py',
        'tools/science_payload_20261016/payload.py', 'tools/whole_child_guard_20261015/guard.py',
        'analysis/sixscan_burst_20261015/qa.py', 'analysis/sixscan_burst_20261015/contract.json'}
    require(required <= observed.keys(), 'Independent QA prerequisites absent from frozen scope')
    limits = scope['resources']
    require(limits['payload_cap_bytes'] == PAYLOAD_CAP and limits['primary_CPU_s'] == 600 and
            limits['qa_CPU_s'] == 600 and limits['primary_QA_wall_s'] == 1800 and
            limits['child_address_space_bytes'] == 1024**3,
            'Independent whole-child conditional bounds differ')
    guard_path = folder.parent / 'process_primary/WAIT4_RECEIPT.json'
    receipt = read(guard_path)
    require(receipt['status'] == 'RESOURCE_COMPLIANT_ONLY' and receipt['resource_acceptance'] is True and
            receipt['wait4_reaped'] is True and receipt['watchdog_fired'] is False and
            receipt['launcher_verified'] is True and receipt['interruption'] is None and
            type(receipt['exit_code']) is int and receipt['exit_code'] == 0 and receipt['errors'] == [],
            'Complete producer whole-child guard acceptance required')
    guard_limits = receipt['limits']
    require(guard_limits['cpu_s'] == 600 and guard_limits['wall_s'] == 1800 and
            guard_limits['address_space_bytes'] == 1024**3, 'Exact producer whole-child guard bounds differ')
    for key, maximum in (('whole_child_CPU_s', 600), ('wall_s', 1800), ('peak_RSS_bytes', 1024**3)):
        value = receipt[key]
        require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= maximum,
                'Producer whole-child measurement invalid: ' + key)
    return scope, observed, guard_path


def verify(folder, report_path):
    folder = Path(folder)
    producer_path = folder / 'PRODUCER.json'
    producer = read(producer_path)
    require(producer['identity'] == IDENTITY, 'Fresh engineering producer identity required')
    require(producer['status'] == 'PRODUCED_COMPLETE_SEARCH_ENGINEERING_ONLY' and
            producer['actual_full_search_performed'] is True and
            producer['RNG_called'] is False and producer['old_scientific_mains_called'] is False,
            'Complete engineering producer provenance required before numerical imports')
    scope, observed_sources, producer_guard_path = _authenticate_scope_and_guard(folder, producer)
    PROGRESS.update(stage='SOURCE_SCOPE_AND_PRODUCER_GUARD_VERIFIED', scope_sha256=producer['scope_sha256'])
    source_pins = producer['legacy_code_pins']
    require(type(source_pins) is dict and 'qa.py' in source_pins and 'contract.json' in source_pins,
            'Frozen legacy QA and coordinate contract pins required')
    for name, pin in source_pins.items():
        require(type(name) is str and '/' not in name and name not in ('.', '..'), 'Invalid legacy source pin path')
        path = LEGACY / name
        require(path.stat().st_size == pin['bytes'] and sha(path) == pin['sha256'],
                'Producer legacy source/contract pin differs: ' + name)
    contract = read(LEGACY / 'contract.json')
    metadata = contract['geometry']['scan_metadata']
    require(len(metadata) == 6 and [s['role'] for s in metadata] == ['ON', 'OFF'] * 3,
            'Complete chronological engineering cadence required')
    loadedfirst, loadedstop = contract['geometry']['loaded_source_channel_interval']
    corefirst, corestop = contract['geometry']['reference_source_channel_interval']
    require(corestop - corefirst == 4096 and loadedstop - loadedfirst == 12096 and corefirst - loadedfirst == 4000,
            'Frozen complete core and loaded margins required')

    import numpy as np
    require(np.__version__ == '2.3.5', 'Frozen independent QA NumPy version differs')
    qa = _load(LEGACY / 'qa.py', 'fullsearch_engineering_unchanged_independent_qa')
    qa.np = np
    transport = _load(TRANSPORT, 'fullsearch_engineering_pinned_payload')
    archive = transport.verify_payload(folder / 'payload', cap=PAYLOAD_CAP,
        expected_semantic_sha256=producer['payload_receipt']['semantic_sha256'],
        max_total_raw_bytes=RAW_EXPANSION_CAP)
    PROGRESS['stage'] = 'PAYLOAD_TRANSPORT_VERIFIED'
    audit = qa.Audit()
    audit.eq(set(archive.tree), {'worker_json', 'worker_arrays', 'legacy_descriptors', 'truth',
        'case', 'admission', 'inputs', 'fixture_spec', 'diagnostic_truth_by_track', 'contract'},
        'Every complete producer root field retained')
    encoded = archive.load(('worker_json',))
    descriptors = archive.load(('legacy_descriptors',))
    found = _descriptor_inventory(encoded, descriptors, audit)
    if 'legacy_descriptors' in producer:
        audit.eq(descriptors, producer['legacy_descriptors'], 'Producer complete original descriptor census')
    audit.eq(len(found), producer['legacy_array_count'], 'Producer complete numerical field count')
    audit.eq([d['path'] for d in archive.descriptors],
        [['worker_arrays', key] for key in found] + [['inputs', meta['scan_id']] for meta in metadata],
        'Every complete legacy result array plus all six raw input fields')
    output = qa.decode(encoded, WorkerArrayStore(archive), audit)
    #QA decode authenticates shape/dtype/all C-order bytes; separately check the
    #original nbytes descriptor at its original source path, rather than trust it.
    for descriptor in found.values():
        value = output
        for component in descriptor['original_field_path']:
            value = value[int(component)] if type(value) is list else value[component]
        audit.eq(value.nbytes, descriptor['nbytes'], 'Complete original numerical nbytes at original path')
    truth = archive.load(('truth',))
    admission = archive.load(('admission',))
    case = archive.load(('case',))
    fixture_spec = archive.load(('fixture_spec',))
    diagnostic_truth = archive.load(('diagnostic_truth_by_track',))
    audit.eq(archive.load(('contract',)), contract, 'Original complete coordinate contract structure')
    audit.eq(type(case).__name__, 'dict', 'Original case remains a dict')
    audit.eq(type(admission).__name__, 'dict', 'Original engineering admission remains a dict')
    audit.eq(type(fixture_spec).__name__, 'dict', 'Original deterministic fixture specification remains a dict')
    audit.eq(output['case_id'], IDENTITY, 'Complete-search output engineering identity')
    audit.eq(case['case_id'], IDENTITY, 'Case engineering identity')
    audit.eq(output['admission'], admission, 'Complete original engineering admission structure')
    audit.eq(admission['scientific_admission'], False, 'Payload cannot establish scientific admission')
    audit.eq(type(admission['scientific_admission']).__name__, 'bool', 'Original admission decision boolean type')
    audit.eq(admission['scope_sha256'], producer['scope_sha256'], 'Exact original admission scope pin')
    audit.eq(admission['observed_source_pins'], observed_sources, 'Every original admission source pin')
    audit.eq(fixture_spec['schema'], 'SETI_DETERMINISTIC_COUNTERHASH_FULLSEARCH_FIXTURE_V1', 'Frozen deterministic fixture specification schema')
    audit.eq(fixture_spec['six_scan_shape'], [6, 16, 12096], 'Complete physical fixture dimensions')
    audit.eq(fixture_spec['RNG_APIs_or_RNG_state_used'], False, 'No random API or state in fixed counter fixture')
    audit.eq(fixture_spec['random_or_independent_noise_law_asserted'], False, 'No statistical noise law asserted')
    audit.eq(fixture_spec['rank_status'], 'NOT_APPLIED_NO_CALIBRATION', 'No unearned rank calibration')
    audit.eq(fixture_spec['probes'], [
        {'name': 'matched', 'scan_indices': [0, 1], 'source_rows': [6, 7, 8, 9],
         'source_channel_offset_from_corefirst': 1024, 'raw_power_excess': 2.0,
         'drift_hz_s': 0.0, 'intrinsic_width_channels': 1},
        {'name': 'primary', 'scan_indices': [2], 'source_rows': [6, 7, 8, 9],
         'source_channel_offset_from_corefirst': 3072, 'raw_power_excess': 2.0,
         'drift_hz_s': 0.0, 'intrinsic_width_channels': 1}], 'Independent physical probe prescription')
    audit.eq(output['qualified_SETI_detection'], False, 'No qualified SETI detection from engineering fixture')
    audit.eq(output['original_A_B'], 'FAIL_CLOSED', 'Closed original qualification remains unchanged')

    times, grid, halo, tables = qa.geometry(contract, corefirst)
    audit.eq(len(grid), 5723, 'Every prescribed global drift-grid member')
    audit.eq(qa.WIDTHS, (1, 3, 9, 33), 'Every prescribed search width')
    audit.eq(qa.WINDOWS, (0, 2, 4, 6, 8, 10, 12), 'Every prescribed four-row search window')
    geometry = output['geometry']
    audit.eq(geometry['core_reference_source_channel_interval_half_open'], [corefirst, corestop], 'Complete ON reference core')
    audit.eq(geometry['OFF_reference_halo_channels'], halo, 'Complete independently derived OFF reference halo')
    audit.eq(geometry['OFF_reference_source_channel_interval_half_open'], [corefirst - halo, corestop + halo], 'Complete OFF reference domain')
    audit.eq(geometry['burst_window_starts'], list(qa.WINDOWS), 'Original complete search window list')
    audit.eq(geometry['widths'], list(qa.WIDTHS), 'Original complete search width list')
    audit.eq(geometry['burst_window_rows'], 4, 'Four-row complete trajectory support')
    audit.close(geometry['drift_grid_hz_s'], grid, 'Whole independent global drift grid', 0.)
    audit.eq([m['scan_id'] for m in output['scan_maps']], [m['scan_id'] for m in metadata], 'Six complete scan-map identities')
    audit.eq(set(output['OFF_threshold_inventories']), {m['scan_id'] for m in metadata if m['role'] == 'OFF'}, 'All complete OFF inventory identities')
    audit.eq(set(output['OFF_inventory_certificates']), {m['scan_id'] for m in metadata if m['role'] == 'OFF'}, 'All complete OFF certificate identities')
    for si, meta in enumerate(metadata):
        PROGRESS.update(stage='INDEPENDENT_COMPLETE_METADATA_GEOMETRY', current_scan=meta['scan_id'])
        audit.close(geometry['times_from_tref_s'][si], times[si], 'Every actual row midpoint coordinate', 0.)
        audit.eq(set(output['alias_geometry'][meta['scan_id']]), {str(k) for k in tables[si]}, 'Every window/parity alias table')
        for key, table in tables[si].items():
            saved = output['alias_geometry'][meta['scan_id']][str(key)]
            order = np.argsort(table['first'])
            renumber = np.empty(len(order), dtype=np.int32)
            renumber[order] = np.arange(len(order), dtype=np.int32)
            for field, expected in (('relative_centers', table['relative'][order]),
                    ('alias_first_index', table['first'][order]), ('alias_last_index', table['last'][order]),
                    ('drift_to_unique_path', renumber[table['inverse']])):
                audit.eq(saved[field].tolist(), expected.tolist(), 'Complete independent native alias geometry ' + field)
            canonical = corefirst - halo + ((key[1] - (corefirst - halo)) % 2)
            audit.eq(saved['canonical_reference_channel'], canonical, 'Independent canonical parity reference')

    own_maps, own_inventories, full_search_checks, independent_hashes = [], {}, [], {}
    authenticated = {}
    for si, meta in enumerate(metadata):
        PROGRESS.update(stage='INDEPENDENT_COMPLETE_SEARCH', current_scan=meta['scan_id'])
        raw = archive.load(('inputs', meta['scan_id']))
        expected = independent_raw(np, si)
        require(type(raw) is np.ndarray and raw.dtype == np.dtype('<f4') and raw.shape == (16, 12096)
                and np.isfinite(raw).all() and (raw >= 0).all(), 'Complete typed finite raw input required')
        independent_hashes[meta['scan_id']] = qa.array_sha(expected)
        audit.eq(qa.array_sha(raw), independent_hashes[meta['scan_id']], 'Independent complete deterministic input byte reconstruction')
        authenticated[meta['scan_id']] = {'shape': [16, 12096], 'dtype': 'float32',
            'C_order_bytes_sha256': independent_hashes[meta['scan_id']], 'nbytes': 16 * 12096 * 4}
        del expected
        own, records, normal, z, maximum = qa.stream_search(raw, si, meta, corefirst, loadedfirst,
            times[si], grid, halo, tables[si], audit)
        saved = output['scan_maps'][si]
        audit.eq(saved['role'], meta['role'], 'Full scan-map role')
        audit.eq({key: type(value).__name__ for key, value in saved['normalization'].items()},
            {key: 'list' for key in (*qa.NORMAL, 'normalization_source_channels', 'normalization_unmasked_counts')},
            'All original normalization fields remain complete Python lists')
        inventory = output['OFF_threshold_inventories'].get(meta['scan_id'])
        certificate = output['OFF_inventory_certificates'].get(meta['scan_id'])
        qa.verify_scan(saved, inventory, certificate, own, records, normal, z, maximum,
            tables[si], grid, corefirst, loadedfirst, audit)
        if certificate is not None:
            audit.eq(certificate['declared_original_grid_hypotheses'], len(own['reference_source_channels']) * 5723 * 7 * 4,
                     'Every declared OFF original-grid hypothesis')
            audit.eq(certificate['score_threshold'], 8., 'Complete OFF inventory threshold')
        own_maps.append(own)
        own_inventories[si] = records
        full_search_checks.append({'scan_id': meta['scan_id'], 'role': meta['role'],
            'carrier_count': len(own['reference_source_channels']),
            'unique_scored': int(own['unique_counts'].sum()),
            'original_grid_scored': len(own['reference_source_channels']) * len(grid) * 7 * 4,
            'OFF_ge8_inventory_rows': len(records), 'maximum': float(maximum),
            'complete_search_recomputed': True, 'complete_retained_maps_checked': True})
        PROGRESS.update(full_search_checks=list(full_search_checks), checks=int(audit.checks),
                        independent_input_hashes=dict(independent_hashes))
        del raw, normal, z
        print(json.dumps({'engineering_QA_scan_complete': meta['scan_id'],
                          'complete_search_recomputed': True, 'CPU_s': time.process_time()}), flush=True)
    audit.eq(producer['input_hashes'], authenticated, 'Producer full input geometry/dtype/hash/byte descriptors')
    audit.eq(output['input_array_hashes'], authenticated, 'Output complete authenticated input descriptors')
    _check_truth(truth, metadata[2]['scan_id'], corefirst + 3072, authenticated, audit)
    audit.eq(set(diagnostic_truth), {'matched'}, 'Independent auxiliary matched-track truth census')
    _check_truth(diagnostic_truth['matched'], metadata[0]['scan_id'], corefirst + 1024, authenticated, audit)
    independent_max = max(float(m['scores'].max()) for meta, m in zip(metadata, own_maps) if meta['role'] == 'ON')
    audit.close(output['maximum_pre_OFF_ON_score'], independent_max, 'Complete-family global pre-OFF ON maximum', 0.)
    audit.close(output['calibrationglobal_ON_max'], independent_max, 'Uncalibrated complete-family maximum alias', 0.)
    qa.verify_hits(output, own_maps, own_inventories, times, grid, metadata, tables, audit)
    recovery = qa.verify_recovery(output, truth, times, grid, metadata, audit)
    matched_output = {**output, 'recovery': output['fixture_diagnostic_recovery']['matched']}
    matched = qa.verify_recovery(matched_output, diagnostic_truth['matched'], times, grid, metadata, audit)
    primary_result = recovery['by_scan'][metadata[2]['scan_id']]
    matched_result = matched['by_scan'][metadata[0]['scan_id']]
    audit.eq(primary_result['pre_OFF'], True, 'Physically isolated engineering probe recovered before OFF')
    audit.eq(primary_result['after_OFF'], True, 'Physically isolated engineering probe retained after OFF')
    audit.eq(matched_result['pre_OFF'], True, 'Physically matched engineering probe recovered before OFF')
    audit.eq(matched_result['after_OFF'], False, 'Physically matched engineering probe vetoed after OFF')
    _authenticate_scope_and_guard(folder, producer)
    PROGRESS.update(stage='COMPLETE_SEARCH_HITS_RECOVERY_AND_SOURCE_RECHECK_PASSED')
    usage = resource.getrusage(resource.RUSAGE_SELF)
    report = {'schema': SCHEMA, 'status': 'PASS_COMPLETE_SEARCH_ENGINEERING_ONLY',
        'identity': IDENTITY, 'mode': MODE, 'case_id': IDENTITY,
        'actual_complete_search_QA_performed': True, 'producer_receipt_sha256': sha(producer_path),
        'producer_guard_receipt_sha256': sha(producer_guard_path), 'scope_sha256': producer['scope_sha256'],
        'payload_semantic_sha256': archive.receipt['semantic_sha256'],
        'payload_manifest_sha256': archive.receipt['manifest_sha256'], 'legacy_code_pins': source_pins,
        'verifier_sha256': sha(Path(__file__)), 'independent_input_hashes': independent_hashes,
        'checks': int(audit.checks), 'maximum_absolute_errors': dict(audit.errors),
        'full_search_checks': full_search_checks,
        'OFF_inventory_checks': {metadata[si]['scan_id']: len(records) for si, records in own_inventories.items()
                                 if metadata[si]['role'] == 'OFF'},
        'independent_global_pre_OFF_ON_maximum': independent_max,
        'independent_recovery': recovery, 'independent_diagnostic_recovery': {'matched': matched},
        'legacy_array_count': len(found), 'normalization_lists_preserved': 36,
        'method': 'Independent integer-coordinate raw reconstruction; unchanged sorted raw501 preprocessing, lexicographic native grouping, complete all-width/all-window/global-grid streaming search; all retained maps and every OFF>=8 record; independent discrete witnesses and truth localization',
        'legacy_QA_functions_exercised': ['decode', 'geometry', 'preprocess (via stream_search)',
            'stream_search', 'verify_scan', 'verify_hits', 'verify_recovery'],
        'self_reported_resources_diagnostic_only': {'cpu_s': usage.ru_utime + usage.ru_stime,
            'wall_s': time.monotonic() - STARTED, 'peak_rss_bytes': usage.ru_maxrss * 1024},
        'whole_process_guard_receipt_required_after_reap': True,
        'calibration_rank_audit': {'applied': False, 'status': 'NOT_APPLIED_NO_CALIBRATION',
                                 'reason': 'No63-case independent calibration bank exists for this deterministic engineering case'},
        'scientific_bank_admission': False, 'scientific_admission': False,
        'sensitivity_or_telescope_FAP_established': False,
        'RNG_called': False, 'old_scientific_mains_called': False,
        'closed_banks_or_observation_checkpoints_read': False,
        'qualified_SETI_detection': False, 'original_A_B': 'FAIL_CLOSED', 'new_observation': False}
    save(report_path, report)
    print(json.dumps({'status': report['status'], 'checks': report['checks'],
                      'full_scans_recomputed': len(full_search_checks),
                      'OFF_inventory_checks': report['OFF_inventory_checks']}), flush=True)
    return report


def main():
    stdout, stderr = BoundedText(sys.stdout), BoundedText(sys.stderr)
    sys.stdout, sys.stderr = stdout, stderr
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        verify(args.folder, args.report)
        require(not stdout.overflow and not stderr.overflow, 'Controlled Python log quota exceeded')
    except BaseException as error:
        if not args.report.exists():
            try:
                save(args.report, {'schema': SCHEMA, 'status': 'FAILED_COMPLETE_SEARCH_ENGINEERING_ONLY',
                    'identity': IDENTITY, 'mode': MODE, 'progress': PROGRESS,
                    'error': {'type': type(error).__name__, 'message': str(error)[:512]},
                    'scientific_bank_admission': False, 'qualified_SETI_detection': False,
                    'original_A_B': 'FAIL_CLOSED', 'retained_no_retry': True})
            except BaseException:
                pass  # Parent guard still retains authoritative failed exit/logs.
        raise


if __name__ == '__main__':
    main()
