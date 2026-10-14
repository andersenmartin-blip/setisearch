"""Create and verify the portable, pinned 2026-10-14 native-path SETI package.

This script reads completed deliverables and frozen inputs; it never changes a
science file. Call only after final documentation/report receipts are complete.
It authenticates all180 scope inputs and all saved science outputs, hashes every
payload, then verifies every archived byte, member count and CRC before writing
an external delivery receipt. The manifest's own hash lives in that receipt.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile

TOP = 'SETI_NATIVE_SPOR_2026-10-14'
EXPECTED_SCOPE_SHA = 'e159332d7a802a0924e2e4eb54c2d0a5467008db716424348de776e3e90a7cb7'
PDF = 'rounding_followup/output/pdf/SETI_native_spor_2026-10-14.pdf'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def pin(path, root):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def conf(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts and
            path.resolve().is_relative_to(root) and not path.is_symlink(), 'Confined input path required: ' + name)
    return path


def auth(root, declared):
    path = conf(root, declared['path'])
    require(path.is_file() and path.stat().st_size == declared['bytes'] and sha(path) == declared['sha256'],
            'Pinned file differs: ' + declared['path'])
    return path


def excluded(path):
    """Exclude intermediate rendering/publication helpers, preserving final v2 plots."""
    parts = path.parts
    name = path.name.lower()
    if any(p.startswith('.') or p == '__pycache__' for p in parts):
        return True
    if path.suffix.lower() in ('.zip', '.pyc', '.pyo'):
        return True
    if parts and parts[0] == 'waterfalls':
        return True
    if tuple(parts[:3]) == ('output', 'pdf', 'tmp_report'):
        return True
    if any(p.lower().startswith(('probe_temp', 'probe_tmp', 'temp_probe', 'tmp_probe')) for p in parts):
        return True
    if any(p.lower() in ('publication_tmp', 'publication_temp', 'publication_inputs', 'publish_tmp', 'publish_inputs') for p in parts):
        return True
    if path.suffix.lower() == '.json' and (re.search(r'(publish|publication).*(input|temp|tmp|payload|args)', name)
                                          or re.search(r'(input|temp|tmp|payload|args).*(publish|publication)', name)):
        return True
    return name in ('delivery_receipt.json', 'package_manifest.json')


def collect(root):
    stage = root / 'rounding_followup'
    scope_path = stage / 'SCOPE.json'
    require(sha(scope_path) == EXPECTED_SCOPE_SHA, 'Frozen observed SCOPE changed')
    scope = read(scope_path)
    require(len(scope['input_pins']) == 180, 'Expected180 frozen input pins')
    declared_paths = set()
    for declared in scope['input_pins']:
        auth(root, declared)
        declared_paths.add(declared['path'])
    require(len(declared_paths) == 180, 'Frozen input pins duplicate a path')
    execution_path = stage / 'results' / 'EXECUTION_RECEIPT.json'
    execution = read(execution_path)
    require(execution['status'] == 'COMPLETE_BOUNDED_EXACT_CONTINUOUS_ROUNDING_PRODUCTION'
            and execution['scope']['sha256'] == EXPECTED_SCOPE_SHA, 'Science execution is incomplete or scope differs')
    require(len(execution['outputs']) == 58, 'Science output pin census differs')
    for declared in execution['outputs']:
        auth(stage / 'results', declared)
    qa_path = stage / 'qa_results' / 'QA_RECEIPT.json'
    qa = read(qa_path)
    require(qa['status'] == 'PASS_INDEPENDENT_EXACT_NUMERICAL_54_CORES_378_COMPLETE_WINDOWS_22235_PATHS_200115_SCORES_3024_INJECTIONS'
            and qa['scope_sha256'] == EXPECTED_SCOPE_SHA and qa['producer_receipt_sha256'] == sha(execution_path),
            'Independent QA does not authenticate completed production')
    require(sha(stage / 'qa.py') == qa['qa_code_sha256'], 'Independent QA source changed after verification')
    require((root / PDF).is_file(), 'Final PDF is absent')
    for path in stage.rglob('*'):
        if not path.is_file():
            continue
        relative_stage = path.relative_to(stage)
        if excluded(relative_stage):
            continue
        require(not path.is_symlink(), 'Stage symlink cannot be packaged')
        declared_paths.add(path.relative_to(root).as_posix())
    require(PDF in declared_paths, 'Final report accidentally excluded')
    require(any(p.startswith('rounding_followup/waterfalls_v2/') and p.endswith('.png') for p in declared_paths), 'Final v2 waterfalls absent')
    # All frozen input paths remain mandatory even if an exclusion expression
    # would normally omit a stage helper; those bytes are needed for replay.
    payload = [pin(conf(root, name), root) for name in sorted(declared_paths)]
    return scope, payload, pin(execution_path, root), pin(qa_path, root), pin(root / PDF, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, help='Workspace base with seti_work/drift_followup/rounding_followup')
    parser.add_argument('--output', help='FreshZIP path; default deliverables/' + TOP + '.zip')
    parser.add_argument('--delivery-receipt', help='Fresh externalJSON path; default deliverables/DELIVERY_RECEIPT.json')
    parser.add_argument('--check-only', action='store_true', help='Verify inputs and report payload census without creating an archive')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    scope, payload, execution_pin, qa_pin, pdf_pin = collect(root)
    if args.check_only:
        print(json.dumps({'status': 'PASS_PORTABLE_NATIVE_PATH_PACKAGE_INPUT_PREFLIGHT',
                          'scope_input_pins_verified': 180, 'science_output_pins_verified': 58,
                          'payload_files_without_manifest': len(payload), 'payload_bytes': sum(p['bytes'] for p in payload),
                          'pdf': pdf_pin, 'archive_created': False}))
        return
    output = Path(args.output).resolve() if args.output else root / 'deliverables' / (TOP + '.zip')
    receipt_path = Path(args.delivery_receipt).resolve() if args.delivery_receipt else root / 'deliverables' / 'DELIVERY_RECEIPT.json'
    require(not output.exists() and not receipt_path.exists(), 'Fresh archive and delivery receipt paths required')
    require(output.suffix.lower() == '.zip' and receipt_path != output and not receipt_path.is_relative_to(root / 'rounding_followup'),
            'External delivery receipt and ZIP output paths required')
    output.parent.mkdir(parents=True, exist_ok=True);receipt_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {'schema': 'SETI_NATIVE_ROUNDING_PORTABLE_PACKAGE_MANIFEST_V1', 'top_folder': TOP,
                'created_utc': datetime.now(timezone.utc).isoformat(),
                'scope_sha256': EXPECTED_SCOPE_SHA, 'scope_input_pins_verified': 180,
                'science_output_pins_verified': 58, 'science_execution_receipt': execution_pin,
                'independent_QA_receipt': qa_pin, 'final_report_pdf': pdf_pin,
                'payload_file_count_without_manifest': len(payload), 'payload_files': payload,
                'manifest_self_hash_location': 'external DELIVERY_RECEIPT.json',
                'paths_preserved_for_portable_replay': True,
                'original_science_files_modified': False}
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')
    manifest_name = TOP + '/PACKAGE_MANIFEST.json'
    expected = {TOP + '/' + p['path']: p for p in payload}
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for declared in payload:
            path = conf(root, declared['path'])
            require(path.stat().st_size == declared['bytes'] and sha(path) == declared['sha256'], 'Payload changed during packaging')
            archive.write(path, TOP + '/' + declared['path'])
        archive.writestr(manifest_name, manifest_bytes)
    with zipfile.ZipFile(output, 'r') as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) == len(payload) + 1 and set(names) == set(expected) | {manifest_name},
                'Archive member census differs')
        require(archive.testzip() is None, 'Archive CRC verification failed')
        for name in names:
            value = hashlib.sha256();count = 0
            with archive.open(name) as stream:
                for block in iter(lambda: stream.read(1048576), b''):
                    value.update(block);count += len(block)
            declared = expected.get(name)
            if declared:
                require(count == declared['bytes'] and value.hexdigest() == declared['sha256'], 'Archive byte verification failed: ' + name)
            else:
                require(count == len(manifest_bytes) and value.hexdigest() == hashlib.sha256(manifest_bytes).hexdigest(), 'Archive manifest byte verification failed')
    # Detect any external writer that changed a packaged payload during ZIP I/O.
    for declared in payload:
        auth(root, declared)
    receipt = {'schema': 'SETI_NATIVE_ROUNDING_DELIVERY_RECEIPT_V1', 'status': 'COMPLETE_ZIP_EVERY_MEMBER_HASH_AND_CRC_VERIFIED',
               'archive': {'path': str(output), 'bytes': output.stat().st_size, 'sha256': sha(output)},
               'top_folder': TOP, 'member_count_including_manifest': len(payload) + 1,
               'payload_file_count_without_manifest': len(payload), 'payload_uncompressed_bytes': sum(p['bytes'] for p in payload),
               'scope_input_pins_verified': 180, 'science_output_pins_verified': 58,
               'manifest': {'archive_member': manifest_name, 'bytes': len(manifest_bytes),
                            'sha256': hashlib.sha256(manifest_bytes).hexdigest()},
               'pdf': pdf_pin, 'scope_sha256': EXPECTED_SCOPE_SHA,
               'science_execution_receipt': execution_pin, 'independent_QA_receipt': qa_pin,
               'packaging_script': pin(Path(__file__).resolve(), root), 'all_member_sha256_and_bytes_verified': True,
               'all_CRC_verified': True, 'original_science_files_modified': False}
    with receipt_path.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True, allow_nan=False);stream.write('\n')
    print(json.dumps({'status': receipt['status'], 'archive': receipt['archive'],
                      'member_count_including_manifest': receipt['member_count_including_manifest'],
                      'delivery_receipt_path': str(receipt_path), 'pdf': pdf_pin}))


if __name__ == '__main__':
    main()
