#!/usr/bin/env python3
"""Independent complete QA of one frozen, postselected2017 source band.

No producer reader, detector, generator, random API or old scientific entrypoint
is imported. Source ZIP/member pins are checked before NumPy/raw NPZ decoding.
The parent must publish the freeze and accept complete engineering first.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1]
LEGACY = SOURCE / 'analysis/sixscan_burst_20261015'
TRANSPORT = SOURCE / 'tools/science_payload_20261016/payload.py'
IDENTITY = 'SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B00'
MODE = 'DESCRIPTIVE_POSTSELECTED_2017'
SCHEMA = 'SETI_DESCRIPTIVE_REAL_FULLSCAN_COMPLETE_QA_V1'
PAYLOAD_CAP = 768 * 1024**2
RAW_EXPANSION_CAP = 800 * 1024**2
REPORT_CAP = 2 * 1024**2
LOG_CAP = 64 * 1024
STARTED = time.monotonic()
PROGRESS = {'stage': 'BEFORE_PREFLIGHT', 'full_search_checks': []}
ARCHIVE_SHA256 = '52b948958c89069a7afb563cf377ee33e4f1324e014428d597b4b3e3a20f6eb3'
ARCHIVE_BYTES = 48468705
CONTEXT_SHA256 = '31efe1e5eeba63d10fbc04ea60bd29eb3086f142b6111a185f821a40a0558522'
ARCHIVE_PREFIX = 'SETI_NATIVE_SPOR_2026-10-14/'
SOURCE_PINS = {
    'epoch1_on': ('e98a0cee33a4c0b249ba363e623354176c7e6fc745dc151b41ec717a7e5f55d3',
                  '941374d6f0d6b985b45a82e04be204af763f43999ad5487b0109d12bb0ee2152', 42317),
    'epoch1_off': ('b61d699b8113ee68cbfaf62d28135fb3b46eaa7fc2d5bf981cceaf8c61103879',
                   'd5ea83c3e481eafd83785a5fedf39620f3d94104556b0bdf9810e33bd9730b95', 42335),
    'epoch2_on': ('d1d7470ff2a083abb30932ac6f9febc8631eb14e8b50c35ad10ba86c2a7395c9',
                  'cd3a141413212b1d66cd8c06ff0389c1f262dbf2b83b90e6c3881ed4bd1ed718', 42303),
    'epoch2_off': ('abf5aba13a5ef886737d7a00c0e6d7d4f7b1d1e851769d0863d027c5b4a2b211',
                   '159478fbaeec200a59e4d82c0d85c3e8261677ad571a5171c46476d1f06b8754', 42281),
    'epoch3_on': ('666eac7fd0c8cdf49265c8d21626d7132f4c914052be8644f014c5206a082e33',
                  '8022a09be65b4af556171a1aaf8e6563f9dc50dd6cbae11529ae490b665a840f', 42312),
    'epoch3_off': ('90a3bbbd0358c031df79421254cbd09eb2f594b18a0732e82712f54ec8cf061f',
                   '4db435b78f445474849d1d215afd499493502cf12fed15300c496371ee003483', 42350),
}


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


def _pin_file(pin, label):
    path = Path(pin['path'])
    require(not path.is_symlink() and path.is_file() and path.stat().st_size == pin['bytes']
            and sha(path) == pin['sha256'], label + ' exact source bytes differ')
    return path


def _preflight(folder, producer):
    scope_path = folder.parent / 'FROZEN_SCOPE.json'
    scope = read(scope_path)
    require(scope['schema'] == 'SETI_FIXED_RETAINED_BAND_COMPLETE_DESCRIPTIVE_SCOPE_V1' and
            scope['mode'] == MODE and scope['identity'] == IDENTITY and
            scope['interpretation']['scientific_bank_admission'] is False and
            sha(scope_path) == producer['scope_sha256'], 'Exact new descriptive source freeze required')
    require(Path(scope['output_root']).resolve() == folder.parent.resolve(), 'Frozen output root differs')
    pins = scope['source_pins']
    require(type(pins) is list and pins, 'Complete source freeze required')
    observed = {}
    for pin in pins:
        relative = Path(pin['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'Unsafe frozen source pin')
        path = (SOURCE / relative).resolve()
        require(SOURCE in path.parents and pin['path'] not in observed, 'Duplicate or outside source pin')
        require(path.stat().st_size == pin['bytes'] and sha(path) == pin['sha256'],
                'Frozen source changed before independent QA: ' + pin['path'])
        observed[pin['path']] = {'bytes': pin['bytes'], 'sha256': pin['sha256']}
    require({'analysis/real_fullscan_20261016/verifier.py', 'tools/science_payload_20261016/payload.py',
             'analysis/sixscan_burst_20261015/qa.py', 'analysis/sixscan_burst_20261015/contract.json'}
            <= observed.keys(), 'Independent descriptive QA prerequisites not frozen')
    resources = scope['resources']
    require(resources['primary_CPU_s'] == 600 and resources['qa_CPU_s'] == 600 and
            resources['child_wall_s'] == 1800 and resources['child_address_space_bytes'] == 1024**3 and
            resources['payload_cap_bytes'] == PAYLOAD_CAP, 'Frozen whole-source conditional caps differ')
    engineering = _pin_file(scope['integration_acceptance'], 'Complete engineering acceptance')
    accepted = read(engineering)
    require(accepted['status'] == 'PASS_COMPLETE_SEARCH_ENGINEERING_ONLY' and
            accepted['scientific_bank_admission'] is False and len(accepted['phases']) == 3 and
            all(p['accepted'] for p in accepted['phases']),
            'Complete engineering PASS must precede real source decoding')
    guard_path = folder.parent / 'process_primary/WAIT4_RECEIPT.json'
    guard = read(guard_path)
    require(guard['status'] == 'RESOURCE_COMPLIANT_ONLY' and guard['resource_acceptance'] is True and
            guard['wait4_reaped'] is True and guard['watchdog_fired'] is False and
            guard['launcher_verified'] is True and guard['interruption'] is None and
            type(guard['exit_code']) is int and guard['exit_code'] == 0 and guard['errors'] == [],
            'Complete parent producer guard acceptance required')
    limits = guard['limits']
    require(limits['cpu_s'] == 600 and limits['wall_s'] == 1800 and
            limits['address_space_bytes'] == 1024**3, 'Exact frozen producer guard caps differ')
    for name, bound in (('whole_child_CPU_s', 600), ('wall_s', 1800), ('peak_RSS_bytes', 1024**3)):
        value = guard[name]
        require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= bound,
                'Invalid whole producer measurement: ' + name)
    return scope, observed, scope_path, guard_path


def _authenticated_source_bytes(scope):
    """Authenticate the original ZIP and all selected members before NPZ decode.

    Only the fixed first canonical band is supported. No retired case identity
    is imported or resumed. Every hash below is a source byte pin rather than
    a score- or outcome-dependent choice. Member bodies remain opaque bytes.
    """
    archive_pin = scope['source_archive']
    require(archive_pin['bytes'] == ARCHIVE_BYTES and archive_pin['sha256'] == ARCHIVE_SHA256,
            'Exact complete original ZIP pin required; damaged copies are not alternate sources')
    path = _pin_file(archive_pin, 'Frozen original source ZIP')
    band = scope['band']
    require(band['native_chunk_index'] == 170 and band['core_q'] == 131 and
            band['reference_source_channel_interval'] == [178794496, 178798592] and
            band['loaded_source_channel_interval'] == [178790496, 178802592],
            'Only the frozen first canonical source band is permitted')
    require([s['scan_id'] for s in band['scans']] == list(SOURCE_PINS), 'Exact six source scan identities required')
    context_pin = scope['source_metadata']
    require(context_pin['bytes'] == 629588 and context_pin['sha256'] == CONTEXT_SHA256 and
            context_pin['member'] == ARCHIVE_PREFIX + 'seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json',
            'Original authenticated source coordinate metadata pin differs')
    wanted = [(context_pin['member'], context_pin['bytes'], context_pin['sha256'])]
    for scan in band['scans']:
        raw_sha, normal_sha, normal_bytes = SOURCE_PINS[scan['scan_id']]
        for field, suffix, size, digest in (
                ('raw_crop', '_raw12096.npz', 808140, raw_sha),
                ('normalization', '_normalization.json', normal_bytes, normal_sha)):
            expected_path = 'seti_work/seti_burst_full/context_results/' + scan['scan_id'] + '_native170_q131' + suffix
            pin = scan[field]
            require(pin['path'] == expected_path and pin['bytes'] == size and pin['sha256'] == digest,
                    'Frozen selected source member pin differs: ' + scan['scan_id'] + ':' + field)
            wanted.append((ARCHIVE_PREFIX + expected_path, size, digest))
    blobs, inventory = {}, {}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        for name, size, digest in wanted:
            require(names.count(name) == 1, 'Missing or duplicate exact source ZIP member: ' + name)
            info = archive.getinfo(name)
            require(not info.is_dir() and not info.flag_bits & 1 and info.file_size == size,
                    'Source member geometry/encryption differs: ' + name)
            with archive.open(info) as stream:
                raw = stream.read(size + 1)
            require(len(raw) == size and hashlib.sha256(raw).hexdigest() == digest,
                    'Source member complete hash/length differs: ' + name)
            blobs[name] = raw
            inventory[name] = {'bytes': size, 'sha256': digest}
    #The exact original archive pin is rechecked after extracting the selected
    #opaque bytes; no source numerical package has been imported at this point.
    _pin_file(archive_pin, 'Frozen original source ZIP after member authentication')
    context = json.loads(blobs[context_pin['member']].decode('utf-8'), object_pairs_hook=_pairs)
    require(type(context) is dict, 'Authenticated original source metadata must remain a dict')
    groups = sorted({(c['native_chunk_index'], c['core_q']) for c in context['normalization_crops']})
    require(len(groups) == 9 and groups[0] == (170, 131) and 'case_id' not in band,
            'Original first-of-nine canonical selection differs; retired identity must not be active')
    for scan in band['scans']:
        records = [c for c in context['normalization_crops'] if
            c['scan_id'] == scan['scan_id'] and c['native_chunk_index'] == 170 and c['core_q'] == 131]
        require(len(records) == 1, 'Exactly one original crop record per selected source scan required')
        record = records[0]
        require(record['source_channel_interval_half_open'] == band['loaded_source_channel_interval'] and
                record['normalization_source_channel_interval_half_open'] == band['reference_source_channel_interval'],
                'Original source metadata selected-band coordinates differ')
        for name in ('raw_crop', 'normalization'):
            original = record[name]
            require(scan[name] == {**original, 'path': 'seti_work/' + original['path']},
                    'Original source metadata selected member declaration differs')
    return blobs, {'archive': archive_pin, 'members': inventory,
                   'all_selected_members_authenticated_before_any_source_NPZ_decode': True}, context


def _decode_source(np, blob, scan_id, loadedfirst, corefirst):
    """Independent NPZ coordinate and raw-power decoder; no producer helpers."""
    with np.load(io.BytesIO(blob), allow_pickle=False) as source:
        fields = ['raw_power', 'source_channel0', 'normalization_source_channels', 'absolute_time_rows']
        require(len(source.files) == 4 and len(set(source.files)) == 4 and set(source.files) == set(fields),
                'Exact original raw NPZ field inventory differs: ' + scan_id)
        first = source['source_channel0']
        channels = source['normalization_source_channels']
        rows = source['absolute_time_rows']
        require(first.shape == () and first.dtype == np.dtype('<i8') and int(first) == loadedfirst,
                'Original raw loaded source coordinate differs: ' + scan_id)
        require(channels.shape == (4096,) and channels.dtype == np.dtype('<i8') and
                np.array_equal(channels, np.arange(corefirst, corefirst + 4096, dtype='<i8')),
                'Original complete normalization source coordinates differ: ' + scan_id)
        require(rows.shape == (16,) and rows.dtype == np.dtype('<i8') and
                np.array_equal(rows, np.arange(16, dtype='<i8')),
                'Original complete source time-row coordinates differ: ' + scan_id)
        raw = source['raw_power']
        require(raw.shape == (16, 12096) and raw.dtype == np.dtype('<f4') and
                np.isfinite(raw).all() and (raw >= 0).all(), 'Original raw power geometry/validity differs: ' + scan_id)
    return np.ascontiguousarray(raw)


def verify(folder, report_path):
    folder = Path(folder)
    producer_path = folder / 'PRODUCER.json'
    producer = read(producer_path, cap=4 * 1024**2)
    require(producer['identity'] == IDENTITY and producer['status'] == 'PRODUCED_DESCRIPTIVE_REAL_FULLSCAN_ONLY'
            and producer['rank_status'] == 'NOT_APPLIED_NO_CALIBRATION', 'New descriptive producer provenance required')
    scope, observed_sources, scope_path, producer_guard_path = _preflight(folder, producer)
    PROGRESS.update(stage='SOURCE_SCOPE_ENGINEERING_PASS_AND_PRODUCER_GUARD_VERIFIED',
                    scope_sha256=producer['scope_sha256'])
    blobs, source_audit, source_context = _authenticated_source_bytes(scope)
    PROGRESS['stage'] = 'ORIGINAL_ZIP_CONTEXT_AND_ALL12_SOURCE_MEMBERS_AUTHENTICATED'
    contract = read(LEGACY / 'contract.json')
    contract['geometry']['loaded_source_channel_interval'] = list(scope['band']['loaded_source_channel_interval'])
    contract['geometry']['reference_source_channel_interval'] = list(scope['band']['reference_source_channel_interval'])
    metadata = contract['geometry']['scan_metadata']
    loadedfirst, loadedstop = contract['geometry']['loaded_source_channel_interval']
    corefirst, corestop = contract['geometry']['reference_source_channel_interval']
    require([m['scan_id'] for m in metadata] == list(SOURCE_PINS) and
            [m['role'] for m in metadata] == ['ON', 'OFF'] * 3 and
            loadedstop - loadedfirst == 12096 and corestop - corefirst == 4096 and corefirst - loadedfirst == 4000,
            'Independent complete original coordinate contract differs')
    for meta in metadata:
        headers = [record['original_header_full'] for record in source_context['source_compacts']
                   if record['scan_id'] == meta['scan_id']]
        require(len(headers) == 3 and all(header == meta['original_header_full'] for header in headers),
                'Original complete source headers differ from the frozen coordinate template')
        attrs = headers[0]['data_attributes']
        require(attrs['tstart'] == meta['tstart_mjd'] and attrs['tsamp'] == meta['tsamp_s'] and
                attrs['fch1'] * 1e6 == meta['fch1_hz'] and attrs['foff'] * 1e6 == meta['df_hz'],
                'Actual original source time/frequency coordinates differ')

    import numpy as np
    require(np.__version__ == '2.3.5', 'Frozen QA NumPy version differs')
    qa = _load(LEGACY / 'qa.py', 'real_fullscan_unchanged_independent_qa')
    qa.np = np
    transport = _load(TRANSPORT, 'real_fullscan_pinned_payload')
    archive = transport.verify_payload(folder / 'payload', cap=PAYLOAD_CAP,
        expected_semantic_sha256=producer['payload_receipt']['semantic_sha256'],
        max_total_raw_bytes=RAW_EXPANSION_CAP)
    audit = qa.Audit()
    audit.eq(set(archive.tree), {'worker_json', 'worker_arrays', 'legacy_descriptors', 'truth',
        'admission', 'case', 'inputs', 'contract'}, 'Every original real-source payload root field')
    audit.eq(archive.load(('contract',)), contract, 'Original complete source coordinate contract retained')
    encoded = archive.load(('worker_json',))
    descriptors = archive.load(('legacy_descriptors',))
    found = _descriptor_inventory(encoded, descriptors, audit)
    audit.eq(len(found), producer['legacy_array_count'], 'Complete original numerical field count')
    audit.eq([d['path'] for d in archive.descriptors],
        [['worker_arrays', key] for key in found] + [['inputs', meta['scan_id']] for meta in metadata],
        'All complete result arrays plus six genuine source raw fields')
    output = qa.decode(encoded, WorkerArrayStore(archive), audit)
    for descriptor in found.values():
        value = output
        for component in descriptor['original_field_path']:
            value = value[int(component)] if type(value) is list else value[component]
        audit.eq(value.nbytes, descriptor['nbytes'], 'Every original complete numerical byte count at original source path')
    truth = archive.load(('truth',)); case = archive.load(('case',)); admission = archive.load(('admission',))
    for label, value in (('truth', truth), ('case', case), ('admission', admission)):
        audit.eq(type(value).__name__, 'dict', 'Original ' + label + ' remains a dict')
        audit.eq(value['case_id'] if label != 'admission' else value['identity'], IDENTITY, 'Fresh descriptive ' + label + ' identity')
    audit.eq(output['case_id'], IDENTITY, 'Actual full-search result descriptive identity')
    audit.eq(output['admission'], admission, 'Original complete descriptive admission structure')
    audit.eq(admission['scope_sha256'], producer['scope_sha256'], 'Exact descriptive admission scope pin')
    audit.eq(admission['observed_source_pins'], observed_sources, 'Every descriptive admission source pin')
    audit.eq(admission['source_receipt'], producer['source_receipt'], 'Original source authentication receipt retained')
    source_receipt = producer['source_receipt']
    audit.eq(source_receipt['source_archive'], scope['source_archive'], 'Producer exact complete original source ZIP pin')
    audit.eq(source_receipt['source_metadata'], scope['source_metadata'], 'Producer original context metadata pin')
    audit.eq(source_receipt['canonical_selection_index'], 0, 'Original canonical first-band selection index')
    expected_member_receipts = []
    for scan in scope['band']['scans']:
        for field in ('raw_crop', 'normalization'):
            member = ARCHIVE_PREFIX + scan[field]['path']
            expected_member_receipts.append({'scan_id': scan['scan_id'], 'field': field, 'member': member,
                **source_audit['members'][member]})
    audit.eq(source_receipt['source_members'], expected_member_receipts,
             'Every independently authenticated original source member receipt')
    audit.eq(admission['scientific_bank_admission'], False, 'No scientific bank admission from postselected source')
    audit.eq(type(admission['scientific_bank_admission']).__name__, 'bool', 'Original admission decision boolean type')
    audit.eq(truth['active_ON_scan_ids'], [], 'No injected or known-source recovery truth')
    audit.eq(type(truth['active_ON_scan_ids']).__name__, 'list', 'Empty original activity remains a list')
    audit.eq(truth['synthetic_injection'], False, 'Actual retained raw source has no synthetic injection')
    audit.eq(output['recovery']['recovery_applicable'], False, 'Original empty-activity recovery ABI is not a measured nonrecovery')
    audit.eq(output['recovery']['active_ON_scan_ids'], [], 'Actual persisted recovery applicability has empty source activity')
    audit.eq(case['family'], 'descriptive_postselected_2017', 'Explicit postselected2017 case family')
    audit.eq(output['rank_status'], 'NOT_APPLIED_NO_CALIBRATION', 'No rank calibration applied to descriptive source')
    audit.eq(output['qualified_SETI_detection'], False, 'No qualified detection claim')
    audit.eq(output['original_A_B'], 'FAIL_CLOSED', 'Original protected qualification remains unchanged')

    times, grid, halo, tables = qa.geometry(contract, corefirst)
    audit.eq(len(grid), 5723, 'Complete global5723-member drift grid')
    audit.eq(qa.WIDTHS, (1, 3, 9, 33), 'All original widths')
    audit.eq(qa.WINDOWS, (0, 2, 4, 6, 8, 10, 12), 'All original four-row windows')
    geometry = output['geometry']
    audit.eq(geometry['core_reference_source_channel_interval_half_open'], [corefirst, corestop], 'Complete actual ON reference source band')
    audit.eq(geometry['OFF_reference_halo_channels'], halo, 'Complete independent OFF reference halo')
    audit.eq(geometry['OFF_reference_source_channel_interval_half_open'], [corefirst - halo, corestop + halo], 'Complete OFF reference source domain')
    audit.eq(geometry['burst_window_starts'], list(qa.WINDOWS), 'Original complete window list retained')
    audit.eq(geometry['widths'], list(qa.WIDTHS), 'Original complete width list retained')
    audit.close(geometry['drift_grid_hz_s'], grid, 'Whole independent global drift grid', 0.)
    audit.eq([m['scan_id'] for m in output['scan_maps']], list(SOURCE_PINS), 'All complete map scan identities')
    off_ids = {m['scan_id'] for m in metadata if m['role'] == 'OFF'}
    audit.eq(set(output['OFF_threshold_inventories']), off_ids, 'Every complete OFF inventory')
    audit.eq(set(output['OFF_inventory_certificates']), off_ids, 'Every complete OFF inventory certificate')
    for si, meta in enumerate(metadata):
        audit.close(geometry['times_from_tref_s'][si], times[si], 'Every actual original row midpoint', 0.)
        saved_tables = output['alias_geometry'][meta['scan_id']]
        audit.eq(set(saved_tables), {str(k) for k in tables[si]}, 'Every window/parity native-alias table')
        for key, table in tables[si].items():
            saved = saved_tables[str(key)]
            order = np.argsort(table['first']); renumber = np.empty(len(order), dtype=np.int32)
            renumber[order] = np.arange(len(order), dtype=np.int32)
            for field, expected in (('relative_centers', table['relative'][order]),
                    ('alias_first_index', table['first'][order]), ('alias_last_index', table['last'][order]),
                    ('drift_to_unique_path', renumber[table['inverse']])):
                audit.eq(saved[field].tolist(), expected.tolist(), 'Complete independent source alias geometry ' + field)
            canonical = corefirst - halo + ((key[1] - (corefirst - halo)) % 2)
            audit.eq(saved['canonical_reference_channel'], canonical, 'Original canonical parity reference')

    own_maps, own_inventories, full_search_checks, input_hashes, authenticated = [], {}, [], {}, {}
    source_normalization_checks = {}
    for si, meta in enumerate(metadata):
        scan_id = meta['scan_id']; PROGRESS.update(stage='INDEPENDENT_COMPLETE_SOURCE_SEARCH', current_scan=scan_id)
        raw_member = ARCHIVE_PREFIX + scope['band']['scans'][si]['raw_crop']['path']
        source = _decode_source(np, blobs[raw_member], scan_id, loadedfirst, corefirst)
        raw = archive.load(('inputs', scan_id))
        require(type(raw) is np.ndarray and raw.shape == (16, 12096) and raw.dtype == np.dtype('<f4'),
                'Complete source input dtype/shape changed in transport')
        input_hashes[scan_id] = qa.array_sha(source)
        audit.eq(qa.array_sha(raw), input_hashes[scan_id], 'Independent complete original source byte reconstruction')
        authenticated[scan_id] = {'shape': [16, 12096], 'dtype': 'float32',
            'C_order_bytes_sha256': input_hashes[scan_id], 'nbytes': 16 * 12096 * 4}
        del source
        own, records, normal, z, maximum = qa.stream_search(raw, si, meta, corefirst, loadedfirst,
            times[si], grid, halo, tables[si], audit)
        saved = output['scan_maps'][si]
        audit.eq(saved['role'], meta['role'], 'Original full source-map role')
        audit.eq({k: type(v).__name__ for k, v in saved['normalization'].items()},
            {k: 'list' for k in (*qa.NORMAL, 'normalization_source_channels', 'normalization_unmasked_counts')},
            'Every original normalization value remains a complete Python list')
        inventory = output['OFF_threshold_inventories'].get(scan_id)
        certificate = output['OFF_inventory_certificates'].get(scan_id)
        qa.verify_scan(saved, inventory, certificate, own, records, normal, z, maximum,
            tables[si], grid, corefirst, loadedfirst, audit)
        if certificate is not None:
            audit.eq(certificate['score_threshold'], 8., 'Original complete OFF inventory threshold')
            audit.eq(certificate['declared_original_grid_hypotheses'], len(own['reference_source_channels']) * 5723 * 7 * 4,
                     'Every declared original OFF-grid hypothesis')
        #The archived normalization sidecar is authenticated as original source
        #provenance. New normalization itself is checked independently above on
        #all4096 selected source channels, with no reuse of archived values.
        normal_member = ARCHIVE_PREFIX + scope['band']['scans'][si]['normalization']['path']
        original_normal = json.loads(blobs[normal_member].decode('utf-8'), object_pairs_hook=_pairs)
        require(type(original_normal) is dict, 'Authenticated normalization sidecar must remain a dict')
        source_normalization_checks[scan_id] = {'sidecar_sha256': hashlib.sha256(blobs[normal_member]).hexdigest(),
            'archived_sidecar_authenticated': True, 'new_selected4096_normalization_recomputed_independently': True,
            'archived_values_used_to_compute_new_scores': False}
        own_maps.append(own); own_inventories[si] = records
        full_search_checks.append({'scan_id': scan_id, 'role': meta['role'],
            'carrier_count': len(own['reference_source_channels']), 'unique_scored': int(own['unique_counts'].sum()),
            'original_grid_scored': len(own['reference_source_channels']) * 5723 * 7 * 4,
            'OFF_ge8_inventory_rows': len(records), 'maximum': float(maximum),
            'complete_search_recomputed': True, 'complete_retained_maps_checked': True})
        PROGRESS.update(full_search_checks=list(full_search_checks), independent_input_hashes=dict(input_hashes),
                        checks=int(audit.checks))
        del raw, normal, z
        print(json.dumps({'descriptive_QA_scan_complete': scan_id, 'CPU_s': time.process_time(),
                          'complete_search_recomputed': True}), flush=True)
    audit.eq(producer['input_hashes'], authenticated, 'All producer raw input coordinates/dtype/hash/byte descriptors')
    audit.eq(truth['authenticated_input_arrays'], authenticated, 'All truth-bound original source input bytes')
    audit.eq(output['input_array_hashes'], authenticated, 'All output-bound original source input bytes')
    independent_max = max(float(m['scores'].max()) for meta, m in zip(metadata, own_maps) if meta['role'] == 'ON')
    audit.close(output['maximum_pre_OFF_ON_score'], independent_max, 'Independent complete-family global pre-OFF ON maximum', 0.)
    qa.verify_hits(output, own_maps, own_inventories, times, grid, metadata, tables, audit)
    recovery = qa.verify_recovery(output, truth, times, grid, metadata, audit)
    audit.eq(recovery['applicable'], False, 'Empty known-activity source does not manufacture recovery measurements')
    _preflight(folder, producer)
    _pin_file(scope['source_archive'], 'Original source ZIP after complete independent QA')
    usage = resource.getrusage(resource.RUSAGE_SELF)
    report = {'schema': SCHEMA, 'status': 'PASS_DESCRIPTIVE_REAL_FULLSCAN_QA_ONLY',
        'identity': IDENTITY, 'mode': MODE, 'scope_sha256': producer['scope_sha256'],
        'producer_receipt_sha256': sha(producer_path), 'producer_guard_receipt_sha256': sha(producer_guard_path),
        'payload_semantic_sha256': archive.receipt['semantic_sha256'],
        'payload_manifest_sha256': archive.receipt['manifest_sha256'], 'source_authentication': source_audit,
        'independent_input_hashes': input_hashes, 'source_normalization_checks': source_normalization_checks,
        'checks': int(audit.checks), 'maximum_absolute_errors': dict(audit.errors),
        'full_search_checks': full_search_checks,
        'OFF_inventory_checks': {metadata[si]['scan_id']: len(r) for si, r in own_inventories.items() if metadata[si]['role'] == 'OFF'},
        'independent_global_pre_OFF_ON_maximum': independent_max,
        'independent_recovery': {'applicable': False, 'status': 'NOT_APPLICABLE_NO_INJECTED_TRUTH'},
        'unchanged_QA_empty_activity_branch_return': recovery,
        'legacy_empty_branch_rank_boolean_is_not_a_statistical_measurement': True,
        'recovery_applicable': False, 'recovery_measurement_available': False,
        'raw_ON_hit_count': len(output['all_ON_threshold_hypotheses']),
        'after_OFF_survivor_count': output['surviving_ON_threshold_hypothesis_count'],
        'legacy_array_count': len(found), 'normalization_lists_preserved': 36,
        'actual_complete_search_QA_performed': True,
        'method': 'Independent original-ZIP and12 source-member authentication; original NPZ coordinates and every raw byte; unchanged complete sorted raw501 preprocessing, lexicographic native grouping, full-width/window/global-drift streaming search, every retained map and OFF>=8 inventory record; all discrete OFF witnesses',
        'self_reported_resources_diagnostic_only': {'cpu_s': usage.ru_utime + usage.ru_stime,
            'wall_s': time.monotonic() - STARTED, 'peak_rss_bytes': usage.ru_maxrss * 1024},
        'whole_process_guard_receipt_required_after_reap': True,
        'rank_status': 'NOT_APPLIED_NO_CALIBRATION', 'statistical_rank_or_calibration_applied': False,
        'ON_count_is_retained_per_carrier_top5_ge10_not_every_scored_ON_ge10': True,
        'OFF_ge8_inventory_is_complete_declared_native4_search_family': True,
        'classification_applied': False, 'scientific_bank_admission': False,
        'sensitivity_or_telescope_FAP_established': False, 'fresh_or_independent_background': False,
        'source_is_postselected_exposed2017_background': True, 'old_scientific_main_or_admission_called': False,
        'RNG_called': False, 'synthetic_injection': False, 'retired_identity_resumed': False,
        'qualified_SETI_detection': False, 'original_A_B': 'FAIL_CLOSED', 'new_observation': False}
    save(report_path, report)
    print(json.dumps({'status': report['status'], 'checks': report['checks'],
        'complete_scans': 6, 'raw_ON_hit_count': report['raw_ON_hit_count'],
        'after_OFF_survivor_count': report['after_OFF_survivor_count']}), flush=True)
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
        require(not stdout.overflow and not stderr.overflow, 'Controlled Python output cap exceeded')
    except BaseException as error:
        if not args.report.exists():
            try:
                save(args.report, {'schema': SCHEMA, 'status': 'FAILED_DESCRIPTIVE_REAL_FULLSCAN_QA_ONLY',
                    'identity': IDENTITY, 'mode': MODE, 'progress': PROGRESS,
                    'error': {'type': type(error).__name__, 'message': str(error)[:512]},
                    'scientific_bank_admission': False, 'qualified_SETI_detection': False,
                    'original_A_B': 'FAIL_CLOSED', 'retained_no_retry': True})
            except BaseException:
                pass
        raise


if __name__ == '__main__':
    main()
