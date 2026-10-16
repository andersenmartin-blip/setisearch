#!/usr/bin/env python3
"""Restore an exact missing ZIP suffix in a NEW byte-transport namespace.

No NumPy, detector, generator, numerical QA or array-value decoder is imported.
The454 complete derived compressed members are copied verbatim. Six original
raw input NPY byte strings are authenticated and repacked, including their ZIP
central directory. Success requires the ENTIRE originally recorded archive
length and SHA-256, plus equality of every retained damaged-file prefix byte.
The original failed B06 execution is never modified, retried or reclassified.
"""
from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import time
import zipfile

import msgpack


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1]
EXPECTED_IDENTITY = 'SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B06'
FAILED_ARCHIVE = {'bytes': 7378998, 'sha256': 'f5332374aff54027ea8e1cfa25738deee7631a61d5a83f88e556b68f4e3f3bed'}
ORIGINAL_ARCHIVE = {'bytes': 8723230, 'sha256': 'b96e21059e3d5480c55aad7788488ba5a49f1f4c05bb59ac14224b5cd09a143a'}
SOURCE_ARCHIVE = {'bytes': 48468705, 'sha256': '52b948958c89069a7afb563cf377ee33e4f1324e014428d597b4b3e3a20f6eb3'}
DERIVED_PREFIX_BYTES = 4761184
DERIVED_MEMBERS = 454
TOTAL_MEMBERS = 460
PHYSICAL_CAP = 64 * 1024**2
METADATA_NAMES = ('MANIFEST.json', 'KEYS.json', 'output.msgpack.gz')
SCAN_IDS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
PREFIX = 'SETI_NATIVE_SPOR_2026-10-14/'
LOG_CAP = 64 * 1024


class BoundedText:
    def __init__(self, stream):
        self.stream, self.remaining, self.overflow = stream, LOG_CAP, False
    def write(self, value):
        value = str(value); raw = value.encode('utf-8', errors='replace')
        kept = raw[:self.remaining]; self.remaining -= len(kept)
        self.overflow |= len(kept) != len(raw)
        self.stream.write(kept.decode('utf-8', errors='ignore')); return len(value)
    def flush(self): self.stream.flush()
    def isatty(self): return False


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Regular original file required')
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1 << 20):
            h.update(block)
    return {'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


def pairs(items):
    result = {}
    for key, value in items:
        require(type(key) is str and key not in result, 'Duplicate/nonstring metadata key')
        result[key] = value
    return result


def read(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 4 * 1024**2,
            'Bounded regular metadata required')
    return json.loads(path.read_text(), object_pairs_hook=pairs)


def save(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    require(len(raw) <= 1024**2, 'Restoration metadata cap exceeded')
    with Path(path).open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def _metadata(payload, manifest):
    for name in METADATA_NAMES:
        if name != 'MANIFEST.json':
            require(pin(payload / name) == manifest['members'][name], 'Original metadata member differs: ' + name)
    keys = read(payload / 'KEYS.json')
    require(type(keys) is list and len(set(keys)) == len(keys), 'Invalid original metadata key pool')

    def key(code, value):
        require(code == 1 and len(value) == 2, 'Unexpected pooled metadata extension')
        number = struct.unpack('>H', value)[0]
        require(number < len(keys), 'Metadata key-pool reference outside inventory')
        return keys[number]

    with gzip.open(payload / 'output.msgpack.gz', 'rb') as stream:
        raw = stream.read(128 * 1024**2 + 1)
    require(len(raw) <= 128 * 1024**2, 'Original unpacked metadata cap exceeded')
    document = msgpack.unpackb(raw, raw=False, strict_map_key=True, ext_hook=key, object_pairs_hook=pairs)
    require(document['schema'] == 'SETI_LOSSLESS_SCIENCE_VALUE_BUNDLE_V1' and
            len(document['arrays']) == TOTAL_MEMBERS, 'Expected exact original complete array inventory required')
    return document


def _local_entries(raw):
    """Read only local ZIP headers/ZIP64 footers; never decompress an array."""
    entries = []
    position = 0
    while True:
        offset = raw.find(b'PK\x03\x04', position)
        if offset < 0:
            break
        position = offset + 4
        try:
            header = struct.unpack_from('<IHHHHHIIIHH', raw, offset)
            nlen, elen = header[-2:]
            name = raw[offset + 30:offset + 30 + nlen].decode('ascii')
        except (struct.error, UnicodeDecodeError):
            continue
        if name != f'array_{len(entries):06d}.npy':
            continue
        require(header[1] == 45 and header[2] == 8 and header[3] == 8 and
                header[6:9] == (0, 0xffffffff, 0xffffffff), 'Original streaming ZIP64 header differs')
        extra = raw[offset + 30 + nlen:offset + 30 + nlen + elen]
        require(extra == bytes.fromhex('0100100000000000000000000000000000000000'), 'Original ZIP64 local extra differs')
        entries.append({'index': len(entries), 'offset': offset, 'header': header,
                        'name': name, 'body_offset': offset + 30 + nlen + elen})
    require(len(entries) == 458 and entries[454]['offset'] == DERIVED_PREFIX_BYTES,
            'Retained local-member census or complete derived prefix differs')
    for current, following in zip(entries, entries[1:]):
        footer = following['offset'] - 24
        signature, crc, compressed, uncompressed = struct.unpack_from('<IIQQ', raw, footer)
        require(signature == 0x08074b50 and current['body_offset'] + compressed == footer,
                'Original complete ZIP64 data-descriptor structure differs')
        current.update(CRC=crc, compress_size=compressed, file_size=uncompressed)
    require(raw.find(b'PK\x01\x02') == -1 and raw.rfind(b'PK\x05\x06') == -1,
            'Expected missing central directory/EOCD differs')
    return entries


def inspect_origin(folder):
    folder = Path(folder)
    payload = folder / 'payload'
    producer = read(folder / 'PRODUCER.json')
    require(producer['identity'] == EXPECTED_IDENTITY and producer['actual_full_search_performed'] is True,
            'Exact already-searched B06 original required')
    manifest = read(payload / 'MANIFEST.json')
    require(pin(payload / 'MANIFEST.json')['sha256'] == producer['payload_receipt']['manifest_sha256'] and
            manifest['members']['science_arrays.npz'] == ORIGINAL_ARCHIVE,
            'Original producer/manifest complete archive target differs')
    require(pin(payload / 'science_arrays.npz') == FAILED_ARCHIVE, 'Retained failed archive bytes changed')
    raw = (payload / 'science_arrays.npz').read_bytes()
    entries = _local_entries(raw)
    document = _metadata(payload, manifest)
    for number, descriptor in enumerate(document['arrays']):
        require(descriptor['key'] == f'array_{number:06d}', 'Original canonical array key order differs')
        if number < DERIVED_MEMBERS:
            require(descriptor['path'][0] == 'worker_arrays' and
                    descriptor['NPY_uncompressed_bytes'] == entries[number]['file_size'],
                    'Original complete derived descriptor/local-header binding differs')
        else:
            require(descriptor['path'] == ['inputs', SCAN_IDS[number - DERIVED_MEMBERS]] and
                    descriptor['shape'] == [16, 12096] and descriptor['dtype'] == '<f4',
                    'Missing suffix is not exclusively the six original raw input fields')
    return {'status': 'FEASIBLE_EXACT_OPAQUE_BYTE_SUFFIX_RESTORATION',
        'origin_folder': str(folder), 'original_failed_archive': FAILED_ARCHIVE,
        'expected_original_archive': ORIGINAL_ARCHIVE,
        'complete_derived_compressed_members': DERIVED_MEMBERS, 'derived_compressed_prefix_bytes': DERIVED_PREFIX_BYTES,
        'retained_local_headers': len(entries), 'first_truncated_member': 'array_000457.npy',
        'truncated_or_missing_fields': ['inputs/epoch2_off', 'inputs/epoch3_on', 'inputs/epoch3_off', 'ZIP central directory/EOCD'],
        'all_complete_ZIP64_data_descriptor_structures_checked': True,
        'intended_source_NPY_repacking': 'Six original authenticated raw_power.npy byte strings, no numerical value decoding',
        'mandatory_acceptance': 'Every retained archive prefix byte plus exact whole originally recorded8723230 bytes and SHA b96e2105...',
        'original_failed_scope_or_files_changed': False, 'scientific_admission': False,
        'detector_or_QA_invocations': 0, 'array_value_decodes': 0}, raw, entries, document


class BoundedUnseekable:
    """Same streaming ZIP behavior as the pinned original array adapter."""
    def __init__(self, path, cap):
        self.stream = Path(path).open('xb')
        self.count, self.cap = 0, cap
    def write(self, value):
        require(self.count + len(value) <= self.cap, 'Restoration physical writer cap exceeded')
        written = self.stream.write(value); self.count += written; return written
    def tell(self): return self.count
    def flush(self): self.stream.flush()
    def __enter__(self): return self
    def __exit__(self, *args):
        self.stream.flush(); os.fsync(self.stream.fileno()); self.stream.close()


def _zip_info(entry):
    header = entry['header']
    clock, date = header[4], header[5]
    stamp = ((date >> 9) + 1980, (date >> 5) & 15, date & 31,
             clock >> 11, (clock >> 5) & 63, (clock & 31) * 2)
    info = zipfile.ZipInfo(entry['name'], stamp)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.flag_bits = 8
    info.create_system = 3
    info.create_version = 45
    info.extract_version = 45
    info.external_attr = 0o600 << 16
    info.header_offset = entry['offset']
    info.CRC = entry['CRC']
    info.compress_size = entry['compress_size']
    info.file_size = entry['file_size']
    return info


def _npy_bytes(raw_npz, descriptor):
    with zipfile.ZipFile(io.BytesIO(raw_npz)) as archive:
        require(archive.namelist().count('raw_power.npy') == 1, 'Unique authenticated original raw NPY member required')
        value = archive.read('raw_power.npy')
    require(value[:8] == b'\x93NUMPY\x01\x00', 'Original raw NPY version must match pinned writer1.0')
    length = struct.unpack_from('<H', value, 8)[0]
    require(length <= 4096, 'Original source NPY header exceeds declared bound')
    header = ast.literal_eval(value[10:10 + length].decode('latin1'))
    require(header == {'descr': '<f4', 'fortran_order': False, 'shape': (16, 12096)}, 'Original source NPY header differs')
    body = value[10 + length:]
    require(len(body) == descriptor['nbytes'] and digest(body) == descriptor['C_order_input_sha256'] and
            len(value) == descriptor['NPY_uncompressed_bytes'], 'Original raw NPY complete body/hash/header-length differs')
    return value


def _source_npy(scope, origin, descriptors):
    source_pin = scope.get('source_inputs', scope['source_archive'])
    require({k: source_pin[k] for k in ('bytes', 'sha256')} == SOURCE_ARCHIVE and
            pin(source_pin['path']) == SOURCE_ARCHIVE, 'Exact authenticated original telescope ZIP required')
    original_scope = read(scope['original_scope']['path'])
    require(original_scope['identity'] == EXPECTED_IDENTITY and original_scope['canonical_index'] == 6 and
            original_scope['source_archive']['sha256'] == SOURCE_ARCHIVE['sha256'], 'Exact original B06 source metadata required')
    result = []
    with zipfile.ZipFile(source_pin['path']) as archive:
        names = archive.namelist()
        for scan, descriptor in zip(original_scope['band']['scans'], descriptors):
            declaration = scan['raw_crop']; member = PREFIX + declaration['path']
            require(names.count(member) == 1, 'Unique original source raw member required')
            raw = archive.read(member)
            require(len(raw) == declaration['bytes'] and digest(raw) == declaration['sha256'], 'Original source raw NPZ byte pin differs')
            result.append(_npy_bytes(raw, descriptor))
    return result


def restore(scope_path, output_root):
    scope_path, output_root = Path(scope_path).resolve(), Path(output_root).resolve()
    scope = read(scope_path)
    require(scope['schema'] == 'SETI_EXACT_SAVED_PAYLOAD_RESTORATION_AND_SEPARATE_QA_SCOPE_V1' and
            scope['mode'] == 'SAVED_RESULT_VERIFICATION_ONLY' and scope['scientific_bank_admission'] is False,
            'Separate frozen transport restoration scope required; cannot admit science')
    for declaration in scope['source_pins']:
        relative = Path(declaration['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'Safe restoration source pin required')
        require(pin(SOURCE / relative) == {k: declaration[k] for k in ('bytes', 'sha256')}, 'Restoration frozen source changed')
    for declaration in scope['origin_evidence_pins'] + [scope['original_scope'], scope['truncated_array_archive']]:
        require(pin(declaration['path']) == {k: declaration[k] for k in ('bytes', 'sha256')}, 'Frozen original evidence changed')
    require(scope['expected_restored_array_archive'] == ORIGINAL_ARCHIVE and
            {k: scope['truncated_array_archive'][k] for k in ('bytes', 'sha256')} == FAILED_ARCHIVE,
            'Frozen exact original/failed archive pins differ')
    origin = Path(scope['origin_folder']).resolve(); restored = Path(scope['restored_folder']).resolve()
    require(restored == output_root / 'observation' and origin != restored and origin not in restored.parents,
            'Restoration must use a NEW output root, never the failed original')
    require(output_root.is_dir() and not restored.exists(), 'Fresh exclusive restored observation directory required')
    scope_sha = pin(scope_path)['sha256']
    require(pin(output_root / 'FROZEN_SCOPE.json')['sha256'] == scope_sha,
            'Exact parent-frozen restoration scope copy required before source NPY bytes')
    resources = scope['resources']
    require(resources['restoration_CPU_s'] == 60 and resources['qa_CPU_s'] == 600 and
            resources['metadata_CPU_s'] == 100 and resources['total_reserved_CPU_s'] == 760 and
            resources['reserved_output_bytes'] == 131 * 1024**2,
            'Complete fresh restoration+QA reservations required')
    global_claim = read(SOURCE.parent / 'work/SAVED_PAYLOAD_CLAIMS_20261016' / (scope['identity'] + '.json'))
    require(global_claim['identity'] == scope['identity'] and global_claim['scope_sha256'] == scope_sha and
            global_claim['reserved_CPU_s'] == 760 and global_claim['reserved_output_bytes'] == resources['reserved_output_bytes']
            and global_claim['no_retry'] is True,
            'Exact exclusive global restoration+QA claim required before source bytes')
    phase_claim = read(output_root / 'CLAIM_restore.json')
    require(phase_claim['identity'] == scope['identity'] and phase_claim['phase'] == 'restore' and
            phase_claim['CPU_reserved_s'] == 60 and phase_claim['output_reserved_bytes'] == 65 * 1024**2 and
            phase_claim['no_retry'] is True,
            'Exact separate60CPU restoration phase claim required before source NPY bytes')
    plan, raw, entries, document = inspect_origin(origin)
    save(output_root / 'RESTORE_CLAIM.json', {'identity': scope['identity'], 'scope_sha256': pin(scope_path)['sha256'],
        'status': 'CLAIMED_ONCE_BEFORE_ORIGINAL_SOURCE_NPY_BYTES_READ', 'original_failed_case_modified': False,
        'no_detector_or_QA_invocations': True, 'array_value_decodes': 0})
    #Source input bytes are read only after the separate frozen parent claim.
    npy_values = _source_npy(scope, origin, document['arrays'][DERIVED_MEMBERS:])
    restored.mkdir(); payload = restored / 'payload'; payload.mkdir()
    for parent, name in [(origin, 'PRODUCER.json')] + [(origin / 'payload', name) for name in METADATA_NAMES]:
        target = restored / name if name == 'PRODUCER.json' else payload / name
        with BoundedUnseekable(target, PHYSICAL_CAP) as stream:
            stream.write((parent / name).read_bytes())
    target = payload / 'science_arrays.npz'
    with BoundedUnseekable(target, PHYSICAL_CAP) as stream:
        stream.write(raw[:DERIVED_PREFIX_BYTES])
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as archive:
            archive.filelist = [_zip_info(entry) for entry in entries[:DERIVED_MEMBERS]]
            archive.NameToInfo = {info.filename: info for info in archive.filelist}
            archive.start_dir = DERIVED_PREFIX_BYTES
            for descriptor, npy in zip(document['arrays'][DERIVED_MEMBERS:], npy_values):
                with archive.open(descriptor['key'] + '.npy', 'w', force_zip64=True) as member:
                    member.write(npy)
    require(pin(target) == ORIGINAL_ARCHIVE, 'Restoration is not the exact originally recorded archive; retain new failure')
    with target.open('rb') as stream:
        require(stream.read(len(raw)) == raw, 'Restoration changed a retained failed-prefix byte')
    with zipfile.ZipFile(target) as archive:
        require(archive.namelist() == [f'array_{i:06d}.npy' for i in range(TOTAL_MEMBERS)] and archive.testzip() is None,
                'Restored exact original archive CRC/inventory check failed')
    require(pin(origin / 'payload/science_arrays.npz') == FAILED_ARCHIVE, 'Original failed file changed during restoration')
    total = sum(path.stat().st_size for path in restored.rglob('*') if path.is_file())
    require(total <= PHYSICAL_CAP, 'Complete restored physical byte quota exceeded')
    receipt = {'status': 'RESTORED_EXACT_ORIGINAL_PAYLOAD_BYTES_ONLY', 'identity': scope['identity'],
        'scope_sha256': pin(scope_path)['sha256'], 'origin_folder': str(origin), 'restored_folder': str(restored),
        'original_failed_archive': FAILED_ARCHIVE, 'restored_archive': pin(target),
        'origin_PRODUCER_sha256': pin(origin / 'PRODUCER.json')['sha256'],
        'original_payload_MANIFEST_sha256': pin(origin / 'payload/MANIFEST.json')['sha256'],
        'derived_compressed_prefix_bytes': DERIVED_PREFIX_BYTES, 'retained_prefix_bytes_match': True,
        'raw_source_NPY_members_repacked': 6, 'numerical_detector_or_QA_invocations': 0, 'array_value_decodes': 0,
        'original_failed_case_modified': False, 'original_cohort_failure_reclassified': False,
        'science_QA_still_required_in_separately_frozen_saved_result_namespace': True,
        'restored_physical_output_bytes': total, 'scientific_bank_admission': False, 'qualified_SETI_detection': False}
    report = Path(scope['restore_receipt_path'])
    require(report == output_root / 'RESTORATION_REPORT.json', 'Fresh restoration receipt path differs')
    save(report, receipt)
    return receipt


def main():
    stdout, stderr = BoundedText(sys.stdout), BoundedText(sys.stderr)
    sys.stdout, sys.stderr = stdout, stderr
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', type=Path, required=True)
    parser.add_argument('--output-root', type=Path)
    parser.add_argument('--plan', action='store_true', help='Inspect retained ZIP metadata only; read no original source NPY bytes')
    parser.add_argument('--plan-output', type=Path)
    args = parser.parse_args()
    if args.plan:
        result = inspect_origin(read(args.scope)['origin_folder'])[0]
        if args.plan_output:
            save(args.plan_output, result)
    else:
        require(args.output_root is not None, '--output-root required for separately claimed restoration')
        result = restore(args.scope, args.output_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    require(not stdout.overflow and not stderr.overflow, 'Restoration Python log quota exceeded')


if __name__ == '__main__':
    main()
