#!/usr/bin/env python3
"""Separate complete QA of an exact restored copy of a saved B06 result.

The numerical verifier and its numerical helpers are byte-identical copies of
the original cohort verifier. Only storage/admission preflight and the report
wrapper differ. Original scope, producer and parent guard receipts are read at
their true origin; arrays are read only from the separately scoped restored
copy. Original B06 failure and cohort incompleteness remain unchanged.

No producer reader, detector, generator, random API or old scientific entrypoint
is imported. Source ZIP/member pins are checked before NumPy/raw NPZ decoding.
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
IDENTITY_PREFIX = 'SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B'
SCAN_IDS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
MODE = 'DESCRIPTIVE_POSTSELECTED_2017'
SCHEMA = 'SETI_DESCRIPTIVE_REAL_COHORT_COMPLETE_CASE_QA_V1'
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


def _case_identity(scope):
    index = scope['canonical_index']
    require(type(index) is int and 1 <= index <= 8, 'Only the eight unattempted canonical indices1..8 are supported')
    identity = IDENTITY_PREFIX + f'{index:02d}'
    require(scope['identity'] == identity, 'New per-band identity must bind exactly its canonical index')
    return identity, index


SAVED_IDENTITY = 'SETI_B06_SAVED_PAYLOAD_RESTORATION_QA_20261016_V1'
SAVED_MODE = 'SAVED_RESULT_VERIFICATION_ONLY'
ORIGINAL_VERIFIER = SOURCE / 'analysis/real_fullscan_cohort_20261016/verifier.py'
ORIGINAL_VERIFIER_SHA256 = 'e70cd7b9096f81df649615e3813aebb9b96ae5bd0658a1486ec3d8443caed022'
TARGET_BYTES = 8723230
TARGET_SHA256 = 'b96e21059e3d5480c55aad7788488ba5a49f1f4c05bb59ac14224b5cd09a143a'
FAILED_BYTES = 7378998
FAILED_SHA256 = 'f5332374aff54027ea8e1cfa25738deee7631a61d5a83f88e556b68f4e3f3bed'
NEW_SCOPE_PATH = None
NEW_SCOPE_SHA256 = None
NEW_OUTPUT_ROOT = None


def _function_text(path, function_name):
    """Read source only; no execution or numerical import in this comparison."""
    import ast
    source = Path(path).read_text()
    parsed = ast.parse(source)
    matches = [node for node in parsed.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
               and node.name == function_name]
    require(len(matches) == 1, 'Exactly one pinned original function/class required: ' + function_name)
    node = matches[0]
    return ''.join(source.splitlines(keepends=True)[node.lineno - 1:node.end_lineno])


def _unchanged_numerical_sources():
    names = ('WorkerArrayStore', '_descriptor_inventory', '_case_identity',
             '_authenticated_source_bytes', '_decode_source', 'verify')
    require(sha(ORIGINAL_VERIFIER) == ORIGINAL_VERIFIER_SHA256,
            'Exact original complete cohort verifier bytes required')
    hashes = {}
    for name in names:
        original = _function_text(ORIGINAL_VERIFIER, name)
        copied = _function_text(Path(__file__), name)
        require(copied == original, 'Copied numerical function/class changed: ' + name)
        hashes[name] = hashlib.sha256(original.encode()).hexdigest()
    return hashes


def _saved_preflight():
    """Authenticate the new storage study without changing original receipts."""
    require(NEW_SCOPE_PATH is not None and NEW_OUTPUT_ROOT is not None, 'Fresh saved-result scope required')
    scope_path, root = Path(NEW_SCOPE_PATH), Path(NEW_OUTPUT_ROOT)
    require(sha(scope_path) == NEW_SCOPE_SHA256 and sha(root / 'FROZEN_SCOPE.json') == NEW_SCOPE_SHA256,
            'Exact fresh saved-result frozen scope bytes required')
    scope = read(scope_path)
    require(scope['schema'] == 'SETI_EXACT_SAVED_PAYLOAD_RESTORATION_AND_SEPARATE_QA_SCOPE_V1'
            and scope['identity'] == SAVED_IDENTITY and scope['mode'] == SAVED_MODE,
            'Separate saved-result namespace/schema/mode required')
    require(Path(scope['output_root']).resolve() == root.resolve()
            and Path(scope['restored_folder']).resolve() == (root / 'observation').resolve(),
            'Fresh restored storage root must match the frozen saved-result scope')
    require(scope['scientific_bank_admission'] is False and scope['no_primary_detector_invocation'] is True
            and scope['original_failure_retained'] is True, 'Saved-result verification cannot reopen the failed cohort')
    observed = {}
    for pin in scope['source_pins']:
        relative = Path(pin['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'Safe fresh source pin required')
        path = (SOURCE / relative).resolve()
        require(SOURCE in path.parents and pin['path'] not in observed, 'Unique source-checkout pin required')
        _pin_file({'path': str(path), 'bytes': pin['bytes'], 'sha256': pin['sha256']}, 'Fresh saved-result code')
        observed[pin['path']] = pin
    require({'tools/saved_payload_restore_20261016/verify.py',
             'tools/saved_payload_restore_20261016/restore.py',
             'tools/saved_payload_restore_20261016/run.py',
             'analysis/real_fullscan_cohort_20261016/verifier.py',
             'analysis/sixscan_burst_20261015/qa.py',
             'tools/science_payload_20261016/payload.py'} <= observed.keys(),
            'Complete fresh saved-result verification freeze required')
    for pin in scope['origin_evidence_pins'] + [scope['truncated_array_archive'], scope['source_archive']]:
        _pin_file(pin, 'Unmodified original evidence')
    original_scope_path = _pin_file(scope['original_scope'], 'Exact original B06 scope')
    require(sha(original_scope_path) == scope['original_scope_sha256'], 'Original scope identity differs')
    origin = Path(scope['origin_folder']).resolve(); restored = Path(scope['restored_folder']).resolve()
    require(origin != restored and origin.parent.name == 'B06' and restored.parent == root.resolve(),
            'Original failed storage and new restored copy must be separate')
    require(read(scope['original_case_result']['path'])['status'] == 'STOPPED_RETAINED_NO_RETRY'
            and read(scope['original_cohort_result']['path'])['status'] == 'INCOMPLETE_COHORT_RETAINED_NO_RETRY',
            'Original case and original cohort must retain their failed/incomplete closures')
    original_npz = origin / 'payload/science_arrays.npz'
    require(original_npz.stat().st_size == FAILED_BYTES and sha(original_npz) == FAILED_SHA256,
            'Retained failed original NPZ must remain byte-for-byte unchanged')
    require(scope['target_npz_bytes'] == TARGET_BYTES and scope['target_npz_sha256'] == TARGET_SHA256
            and scope['expected_restored_array_archive'] == {'bytes': TARGET_BYTES, 'sha256': TARGET_SHA256},
            'Only the exact original pre-failure saved archive can be verified')
    restored_npz = restored / 'payload/science_arrays.npz'
    require(restored_npz.stat().st_size == TARGET_BYTES and sha(restored_npz) == TARGET_SHA256,
            'Restored copy must match the exact original pre-failure archive bytes')
    require(sha(restored / 'PRODUCER.json') == sha(origin / 'PRODUCER.json'),
            'Original producer receipt must be copied unchanged, never forged')
    for name in ('MANIFEST.json', 'KEYS.json', 'output.msgpack.gz'):
        require(sha(restored / 'payload' / name) == sha(origin / 'payload' / name),
                'Original saved metadata must remain byte-for-byte unchanged: ' + name)
    claim_path = SOURCE.parent / 'work/SAVED_PAYLOAD_CLAIMS_20261016' / (SAVED_IDENTITY + '.json')
    claim = read(claim_path)
    require(claim['identity'] == SAVED_IDENTITY and claim['scope_sha256'] == NEW_SCOPE_SHA256
            and claim['no_retry'] is True and claim['reserved_CPU_s'] == 760,
            'Fresh once-only saved-result claim must precede numerical verification')
    report_path = Path(scope['restore_receipt_path'])
    restoration = read(report_path)
    require(restoration['status'] == 'RESTORED_EXACT_ORIGINAL_PAYLOAD_BYTES_ONLY'
            and restoration['identity'] == SAVED_IDENTITY and restoration['scope_sha256'] == NEW_SCOPE_SHA256
            and restoration['scientific_bank_admission'] is False,
            'Exact completed restoration report required before independent QA')
    restore_guard_path = root / 'process_restore/WAIT4_RECEIPT.json'
    guard = read(restore_guard_path)
    require(guard['resource_acceptance'] is True and guard['status'] == 'RESOURCE_COMPLIANT_ONLY'
            and guard['wait4_reaped'] is True and guard['launcher_verified'] is True
            and guard['watchdog_fired'] is False and guard['interruption'] is None
            and guard['exit_code'] == 0 and guard['errors'] == [],
            'Whole restoration child must close before independent verification')
    resources = scope['resources']
    limits = guard['limits']
    require(resources['restoration_CPU_s'] == 60 and resources['qa_CPU_s'] == 600
            and resources['child_wall_s'] == 1800 and resources['child_address_space_bytes'] == 1024**3
            and limits['cpu_s'] == 60 and limits['wall_s'] == 1800
            and limits['address_space_bytes'] == 1024**3,
            'Exact new saved-result prospective process bounds required')
    for name, bound in (('whole_child_CPU_s', 60), ('wall_s', 1800), ('peak_RSS_bytes', 1024**3)):
        value = guard[name]
        require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= bound,
                'Invalid whole restoration measurement: ' + name)
    phase = read(root / 'PHASE_restore.json')
    require(phase['status'] == 'ACCEPTED_SEPARATE_RESTORATION_STUDY_PHASE'
            and phase['phase'] == 'restore' and phase['receipt'] == guard
            and phase['report_sha256'] == sha(report_path),
            'Parent acceptance of the whole restoration phase must precede numerical QA')
    return scope, _unchanged_numerical_sources()


def _preflight(folder, producer):
    """Explicitly separate original provenance from new copy storage.

    All original numerical/QA functions below remain byte-for-byte identical.
    The original preflight authenticates original scope/producer/guard receipts
    at their true origin paths. It never examines the failed original arrays.
    Fresh saved-result admission and restored-file hashes are checked separately.
    """
    saved, _ = _saved_preflight()
    origin, restored = Path(saved['origin_folder']), Path(saved['restored_folder'])
    require(Path(folder).resolve() == restored.resolve(), 'Numerical QA may load only the new restored copy')
    original = _load(ORIGINAL_VERIFIER, 'saved_result_original_preflight_only')
    result = original._preflight(origin, producer)
    require(result[0]['identity'] == saved['original_case_id']
            and result[0]['canonical_index'] == saved['canonical_index'] == 6
            and sha(result[2]) == saved['original_scope_sha256'],
            'Original B06 provenance must remain bound to the separately restored saved result')
    return result


def _authenticated_source_bytes(scope):
    """Authenticate the original ZIP and all selected members before NPZ decode.

    The whole original context-metadata member is authenticated before deriving
    this fixed canonical band's twelve source member pins. No producer reader
    or B00 numerical source is imported or resumed. Bodies remain opaque bytes.
    """
    archive_pin = scope['source_archive']
    require(archive_pin['bytes'] == ARCHIVE_BYTES and archive_pin['sha256'] == ARCHIVE_SHA256,
            'Exact complete original ZIP pin required; damaged copies are not alternate sources')
    path = _pin_file(archive_pin, 'Frozen original source ZIP')
    band = scope['band']
    identity, index = _case_identity(scope)
    require([s['scan_id'] for s in band['scans']] == list(SCAN_IDS), 'Exact six source scan identities required')
    context_pin = scope['source_metadata']
    require(context_pin['bytes'] == 629588 and context_pin['sha256'] == CONTEXT_SHA256 and
            context_pin['member'] == ARCHIVE_PREFIX + 'seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json',
            'Original authenticated source coordinate metadata pin differs')
    blobs, inventory = {}, {}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()

        def member_bytes(name, size, digest):
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
            return raw

        raw_context = member_bytes(context_pin['member'], context_pin['bytes'], context_pin['sha256'])
        context = json.loads(raw_context.decode('utf-8'), object_pairs_hook=_pairs)
        require(type(context) is dict, 'Authenticated original source metadata must remain a dict')
        groups = sorted({(c['native_chunk_index'], c['core_q']) for c in context['normalization_crops']})
        require(groups == [(170, 131), (170, 252), (171, 55), (171, 231), (172, 12),
                           (172, 48), (172, 81), (172, 94), (172, 168)],
                'Whole original canonical nine-band metadata inventory differs')
        chosen = groups[index]
        require((band['native_chunk_index'], band['core_q']) == chosen and 'case_id' not in band,
                'Frozen canonical band differs or attempts to reuse a retired case identity')
        for scan in band['scans']:
            records = [c for c in context['normalization_crops'] if
                c['scan_id'] == scan['scan_id'] and (c['native_chunk_index'], c['core_q']) == chosen]
            require(len(records) == 1, 'Exactly one original crop record per selected source scan required')
            record = records[0]
            require(record['source_channel_interval_half_open'] == band['loaded_source_channel_interval'] and
                    record['normalization_source_channel_interval_half_open'] == band['reference_source_channel_interval'],
                    'Original source metadata selected-band coordinates differ')
            for field in ('raw_crop', 'normalization'):
                original = record[field]
                expected = {**original, 'path': 'seti_work/' + original['path']}
                require(scan[field] == expected, 'Frozen source member pin differs from authenticated original metadata')
                relative = Path(expected['path'])
                require(not relative.is_absolute() and '..' not in relative.parts,
                        'Original source member must remain inside the authenticated ZIP namespace')
                member_bytes(ARCHIVE_PREFIX + expected['path'], expected['bytes'], expected['sha256'])
    #The exact original archive pin is rechecked after extracting the selected
    #opaque bytes; no source numerical package has been imported at this point.
    _pin_file(archive_pin, 'Frozen original source ZIP after member authentication')
    return blobs, {'archive': archive_pin, 'members': inventory,
                   'identity': identity, 'canonical_index': index,
                   'canonical_native_chunk_index': chosen[0], 'canonical_core_q': chosen[1],
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
    require(producer['status'] == 'PRODUCED_DESCRIPTIVE_REAL_FULLSCAN_ONLY'
            and producer['rank_status'] == 'NOT_APPLIED_NO_CALIBRATION', 'New descriptive producer provenance required')
    scope, observed_sources, scope_path, producer_guard_path = _preflight(folder, producer)
    identity, index = _case_identity(scope)
    PROGRESS.update(stage='SOURCE_SCOPE_ENGINEERING_PASS_AND_PRODUCER_GUARD_VERIFIED',
                    identity=identity, canonical_index=index, scope_sha256=producer['scope_sha256'])
    blobs, source_audit, source_context = _authenticated_source_bytes(scope)
    PROGRESS['stage'] = 'ORIGINAL_ZIP_CONTEXT_AND_ALL12_SOURCE_MEMBERS_AUTHENTICATED'
    contract = read(LEGACY / 'contract.json')
    contract['geometry']['loaded_source_channel_interval'] = list(scope['band']['loaded_source_channel_interval'])
    contract['geometry']['reference_source_channel_interval'] = list(scope['band']['reference_source_channel_interval'])
    metadata = contract['geometry']['scan_metadata']
    loadedfirst, loadedstop = contract['geometry']['loaded_source_channel_interval']
    corefirst, corestop = contract['geometry']['reference_source_channel_interval']
    require([m['scan_id'] for m in metadata] == list(SCAN_IDS) and
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
    qa = _load(LEGACY / 'qa.py', 'real_fullscan_cohort_unchanged_independent_qa')
    qa.np = np
    transport = _load(TRANSPORT, 'real_fullscan_cohort_pinned_payload')
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
        audit.eq(value['case_id'] if label != 'admission' else value['identity'], identity, 'Fresh descriptive ' + label + ' identity')
    audit.eq(output['case_id'], identity, 'Actual full-search result descriptive identity')
    audit.eq(output['canonical_index'], index, 'Actual full-search canonical band index')
    audit.eq(output['case_index'], index, 'Original complete output case index')
    audit.eq(case['canonical_index'], index, 'Saved case canonical band index')
    audit.eq(case['selection_index'], index, 'Saved case selection index')
    audit.eq(case['native_chunk_index'], scope['band']['native_chunk_index'], 'Saved case original native chunk')
    audit.eq(case['core_q'], scope['band']['core_q'], 'Saved case original core subdivision')
    audit.eq(output['admission'], admission, 'Original complete descriptive admission structure')
    audit.eq(admission['scope_sha256'], producer['scope_sha256'], 'Exact descriptive admission scope pin')
    audit.eq(admission['observed_source_pins'], observed_sources, 'Every descriptive admission source pin')
    audit.eq(admission['source_receipt'], producer['source_receipt'], 'Original source authentication receipt retained')
    source_receipt = producer['source_receipt']
    audit.eq(source_receipt['source_archive'], scope['source_archive'], 'Producer exact complete original source ZIP pin')
    audit.eq(source_receipt['source_metadata'], scope['source_metadata'], 'Producer original context metadata pin')
    audit.eq(source_receipt['canonical_selection_index'], index, 'Original remaining canonical-band selection index')
    audit.eq(source_receipt['native_chunk_index'], scope['band']['native_chunk_index'], 'Original member source native chunk')
    audit.eq(source_receipt['core_q'], scope['band']['core_q'], 'Original member source core subdivision')
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
    audit.eq([m['scan_id'] for m in output['scan_maps']], list(SCAN_IDS), 'All complete map scan identities')
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
        'identity': identity, 'canonical_index': index, 'mode': MODE, 'scope_sha256': producer['scope_sha256'],
        'producer_receipt_sha256': sha(producer_path), 'producer_guard_receipt_sha256': sha(producer_guard_path),
        'producer_phase_receipt_sha256': sha(folder.parent / 'PHASE_primary.json'),
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
    global NEW_SCOPE_PATH, NEW_SCOPE_SHA256, NEW_OUTPUT_ROOT
    stdout, stderr = BoundedText(sys.stdout), BoundedText(sys.stderr)
    sys.stdout, sys.stderr = stdout, stderr
    parser = argparse.ArgumentParser(description='Verify an exact restored copy under a new saved-result scope; original B06 remains failed.')
    parser.add_argument('--scope', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--scope-sha256')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    NEW_SCOPE_PATH = args.scope.resolve()
    NEW_OUTPUT_ROOT = args.output_root.resolve()
    NEW_SCOPE_SHA256 = args.scope_sha256 or sha(NEW_OUTPUT_ROOT / 'FROZEN_SCOPE.json')
    report_path = (args.report or NEW_OUTPUT_ROOT / 'SAVED_QA_REPORT.json').resolve()
    numerical_path = NEW_OUTPUT_ROOT / 'NUMERICAL_QA_REPORT.json'
    require(report_path.parent == NEW_OUTPUT_ROOT and not report_path.exists() and not numerical_path.exists(),
            'Fresh, separately named numerical and wrapper reports required')
    try:
        saved, unchanged = _saved_preflight()
        numerical = verify(Path(saved['restored_folder']), numerical_path)
        require(numerical['status'] == 'PASS_DESCRIPTIVE_REAL_FULLSCAN_QA_ONLY'
                and numerical['actual_complete_search_QA_performed'] is True,
                'Original unchanged complete numerical QA must pass on the restored saved result')
        _saved_preflight()
        report = {'schema': 'SETI_SEPARATE_RESTORED_SAVED_RESULT_COMPLETE_QA_V1',
            'status': 'PASS_RESTORED_SAVED_DESCRIPTIVE_SEARCH_QA_ONLY',
            'identity': SAVED_IDENTITY, 'mode': SAVED_MODE,
            'scope_sha256': NEW_SCOPE_SHA256, 'original_case_identity': numerical['identity'],
            'original_scope_sha256': saved['original_scope_sha256'],
            'origin_folder': saved['origin_folder'], 'restored_folder': saved['restored_folder'],
            'exact_restored_array_archive': {'bytes': TARGET_BYTES, 'sha256': TARGET_SHA256},
            'original_failed_array_archive_retained': {'bytes': FAILED_BYTES, 'sha256': FAILED_SHA256},
            'original_case_status': 'STOPPED_RETAINED_NO_RETRY',
            'original_cohort_status': 'INCOMPLETE_COHORT_RETAINED_NO_RETRY',
            'original_failure_and_cohort_unchanged': True,
            'numerical_report_path': str(numerical_path), 'numerical_report_sha256': sha(numerical_path),
            'numerical_report_schema': numerical['schema'], 'numerical_report_status': numerical['status'],
            'original_verifier_sha256': ORIGINAL_VERIFIER_SHA256,
            'unchanged_numerical_function_source_sha256': unchanged,
            'complete_saved_search_recomputed_by_independent_QA': True,
            'primary_detector_or_generator_invoked': False,
            'new_saved_result_verification_is_original_case_retry': False,
            'checks': numerical['checks'], 'legacy_array_count': numerical['legacy_array_count'],
            'full_search_checks': numerical['full_search_checks'],
            'maximum_absolute_errors': numerical['maximum_absolute_errors'],
            'independent_input_hashes': numerical['independent_input_hashes'],
            'raw_ON_hit_count': numerical['raw_ON_hit_count'],
            'after_OFF_survivor_count': numerical['after_OFF_survivor_count'],
            'OFF_inventory_checks': numerical['OFF_inventory_checks'],
            'independent_global_pre_OFF_ON_maximum': numerical['independent_global_pre_OFF_ON_maximum'],
            'restore_guard_receipt_sha256': sha(NEW_OUTPUT_ROOT / 'process_restore/WAIT4_RECEIPT.json'),
            'restoration_report_sha256': sha(saved['restore_receipt_path']),
            'original_producer_receipt_sha256': numerical['producer_receipt_sha256'],
            'original_producer_guard_receipt_sha256': numerical['producer_guard_receipt_sha256'],
            'rank_status': 'NOT_APPLIED_NO_CALIBRATION', 'recovery_measurement_available': False,
            'scientific_bank_admission': False, 'qualified_SETI_detection': False,
            'sensitivity_or_telescope_FAP_established': False,
            'original_A_B': 'FAIL_CLOSED', 'new_observation': False}
        require(not stdout.overflow and not stderr.overflow, 'Controlled Python output cap exceeded')
        save(report_path, report)
        print(json.dumps({'status': report['status'], 'identity': SAVED_IDENTITY,
                          'checks': report['checks'], 'original_failure_and_cohort_unchanged': True}), flush=True)
    except BaseException as error:
        if not numerical_path.exists():
            save(numerical_path, {'schema': SCHEMA, 'status': 'FAILED_DESCRIPTIVE_REAL_FULLSCAN_QA_ONLY',
                'identity': PROGRESS.get('identity'), 'mode': MODE, 'progress': PROGRESS,
                'error': {'type': type(error).__name__, 'message': str(error)[:512]},
                'scientific_bank_admission': False, 'qualified_SETI_detection': False,
                'original_A_B': 'FAIL_CLOSED', 'retained_no_retry': True})
        if not report_path.exists():
            save(report_path, {'schema': 'SETI_SEPARATE_RESTORED_SAVED_RESULT_COMPLETE_QA_V1',
                'status': 'FAILED_RESTORED_SAVED_DESCRIPTIVE_SEARCH_QA_ONLY',
                'identity': SAVED_IDENTITY, 'mode': SAVED_MODE, 'scope_sha256': NEW_SCOPE_SHA256,
                'original_case_identity': 'SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B06',
                'original_failure_and_cohort_unchanged': True,
                'error': {'type': type(error).__name__, 'message': str(error)[:512]},
                'numerical_report_sha256': sha(numerical_path),
                'scientific_bank_admission': False, 'qualified_SETI_detection': False,
                'original_A_B': 'FAIL_CLOSED', 'retained_no_retry': True})
        raise


if __name__ == '__main__':
    main()
