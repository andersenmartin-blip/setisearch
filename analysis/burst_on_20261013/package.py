"""Assemble a completed ON-burst/context package without opening arrays.

Only opaque byte hashing and JSON metadata checks are performed. --preflight
has no output writes. --build is admitted only after all primary/context and
independent QA receipts are complete. Original HDF5 and runtime wheels remain
external prerequisites for the full-source primary audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile

sys.dont_write_bytecode = True
BASE = 'seti_burst_on'
JOBS = ('on20170428_epoch1_HIP98505', 'on20170428_epoch2_HIP98505', 'on20170428_epoch3_HIP98505')
PRIMARY_STATUS = 'COMPLETE_96_NEW_ON_BURST4_COMBINED_MAPS_EXPLORATORY_ONLY'
CONTEXT_STATUS = 'COMPLETE_NINE_ON_BURST4_FIXED_TRACKS54_SIX_SCAN_CONTEXTS'
PRIMARY_QA_STATUS = 'PASS288_ON_BURST4_MAPS1170_RAW4X503_QUERIES144_SOURCE_ROWS_NO_GRID_RERUN'
CONTEXT_QA_STATUS = 'PASS54_FIXED_SIX_SCAN_PROFILES9_OWN_SCORES_ALL_FULL501_NORMALIZATIONS'
EXTRA_ORIGINALS = ('burst_previous/analysis/new_visit_search/dependencies/standard_reader.py',
                   'burst_previous/analysis/RESTORATION_RECEIPT_20261011.json')
ALLOWED_SUFFIXES = {'.py', '.json', '.md', '.txt', '.log', '.csv', '.png', '.jpg', '.svg', '.pdf', '.npz'}
FORBIDDEN_SUFFIXES = {'.h5', '.hdf5', '.whl', '.lock', '.pyc', '.zip', '.part01', '.part02', '.part03'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_bytes(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def confined(root, name):
    name = Path(name)
    path = root / name
    require(not name.is_absolute() and '..' not in name.parts and not path.is_symlink() and
            path.resolve().is_relative_to(root), 'Confined ordinary relative project path required')
    return path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def pin(root, path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def require_pin(root, declaration):
    path = confined(root, declaration['path'])
    require(pin(root, path) == {k: declaration[k] for k in ('path', 'bytes', 'sha256')},
            'Authenticated file pin differs: ' + declaration['path'])
    return path


def prospective_inventory(root):
    """Names/sizes only; may be used while numerical producers are unfinished."""
    jobs = {}
    for job in JOBS:
        folder = root / BASE / 'results' / job
        arrays = list(folder.glob('*.npz'))
        audits = [p for p in arrays if p.name.endswith('_raw4x503.npz')]
        jobs[job] = {'saved_map_files': len(arrays) - len(audits), 'expected_map_files': 96,
                     'saved_audit_files': len(audits), 'expected_audit_files': 390,
                     'execution_receipt_present': (folder / 'EXECUTION_RECEIPT.json').is_file()}
    context = root / BASE / 'context_results'
    dependencies = set(EXTRA_ORIGINALS)
    for filename, field in (('SCOPE.json', 'text_code_pins'), ('CONTEXT_SCOPE.json', 'input_pins')):
        path = root / BASE / filename
        if path.is_file():
            dependencies.update(p['path'] for p in read(path)[field])
    return {'status': 'PROSPECTIVE_NAMES_AND_SIZES_ONLY_COMPLETION_NOT_ASSUMED', 'primary_jobs': jobs,
            'context_raw503_files': len(list(context.glob('*_raw503.npz'))),
            'context_raw12096_files': len(list(context.glob('*_raw12096.npz'))),
            'metadata_dependencies': sorted(dependencies),
            'source_HDF5_excluded': True, 'runtime_wheels_excluded': True,
            'numerical_arrays_opened': False, 'byte_hashes_of_array_payloads_read': False,
            'archive_built': False, 'output_files_written': False}


def completed_inputs(root, primary_qa_path, context_qa_path):
    """Validate completion and opaque byte pins; never import NumPy/HDF5."""
    primary_scope_path = root / BASE / 'SCOPE.json'
    context_scope_path = root / BASE / 'CONTEXT_SCOPE.json'
    primary_scope, context_scope = read(primary_scope_path), read(context_scope_path)
    primary_scope_sha, context_scope_sha = digest(primary_scope_path), digest(context_scope_path)
    require(primary_scope['total_maps'] == 288 and context_scope['context_profiles'] == 54 and
            len(context_scope['selected_tracks']) == 9, 'Completed package scope counts differ')
    receipts, counts = [], {'primary_maps': 0, 'primary_raw4x503_audits': 0,
                           'context_profiles': 54, 'context_raw16x503_capsules': 54}
    receipt_hashes = {}
    for job in JOBS:
        folder = root / BASE / 'results' / job
        path = folder / 'EXECUTION_RECEIPT.json'
        receipt = read(path)
        require(receipt['status'] == PRIMARY_STATUS and receipt['scope_sha256'] == primary_scope_sha and
                receipt['counts']['maps'] == 96 and receipt['counts']['score_audit_queries'] == 390,
                'All three completed primary96 map/390 audit receipts required')
        for declaration in receipt['output_byte_pins']:
            require_pin(root, declaration)
        actual_maps = [p for p in folder.glob('*.npz') if not p.name.endswith('_raw4x503.npz')]
        actual_audits = list(folder.glob('*_raw4x503.npz'))
        require(len(actual_maps) == 96 and len(actual_audits) == 390, 'Primary saved map/audit census differs')
        counts['primary_maps'] += len(actual_maps)
        counts['primary_raw4x503_audits'] += len(actual_audits)
        receipts.append(pin(root, path))
        receipt_hashes[job] = digest(path)
    context_path = root / BASE / 'context_results' / 'EXECUTION_RECEIPT.json'
    context = read(context_path)
    require(context['status'] == CONTEXT_STATUS and context['context_scope_sha256'] == context_scope_sha and
            context['counts']['context_profiles'] == 54 and context['counts']['origin_score_matches'] == 9,
            'Completed54 fixed contexts/nine own score matches required')
    for declaration in context['output_pins']:
        require_pin(root, declaration)
    crops = list((root / BASE / 'context_results').glob('*_raw12096.npz'))
    profiles = list((root / BASE / 'context_results').glob('*_raw503.npz'))
    require(len(crops) == context['counts']['raw_normalization_crops'] and len(profiles) == 54,
            'Saved full16 normalization crop/profile census differs')
    counts['context_raw16x12096_normalization_crops'] = len(crops)
    context_sha = digest(context_path)
    primary_qa_file = confined(root, primary_qa_path)
    context_qa_file = confined(root, context_qa_path)
    primary_qa, context_qa = read(primary_qa_file), read(context_qa_file)
    require(primary_qa['status'] == PRIMARY_QA_STATUS and primary_qa['primary_scope_sha256'] == primary_scope_sha and
            primary_qa['primary_receipt_sha256s'] == receipt_hashes,
            'Completed independent primary QA bound to exact three receipts required')
    require(context_qa['status'] == CONTEXT_QA_STATUS and
            context_qa['context_receipt_sha256'] == context_sha and
            context_qa.get('context_scope_sha256') == context_scope_sha,
            'Completed independent context QA bound to exact context receipt/scope required')
    names = set()
    for path in (root / BASE).rglob('*'):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part.startswith('.') or part in ('__pycache__', 'package_outputs') for part in relative.parts):
            continue
        if path.suffix in FORBIDDEN_SUFFIXES or path.suffix not in ALLOWED_SUFFIXES:
            continue
        names.add(relative.as_posix())
    # Current scope pins are the minimal executable metadata dependency closure.
    # Original historical result arrays and their large delivery trees are omitted.
    for declaration in primary_scope['text_code_pins'] + context_scope['input_pins']:
        path = require_pin(root, declaration)
        require(path.suffix in {'.py', '.json', '.md', '.txt'}, 'Scope dependency must be text/code')
        names.add(path.relative_to(root).as_posix())
    for name in EXTRA_ORIGINALS:
        require(confined(root, name).is_file(), 'Original external-source audit metadata missing: ' + name)
        names.add(name)
    names.add(primary_qa_path)
    names.add(context_qa_path)
    require(BASE + '/REPLAY_README.md' in names, 'Portable replay README required')
    for name in names:
        path = confined(root, name)
        require(path.suffix not in FORBIDDEN_SUFFIXES and path.suffix in ALLOWED_SUFFIXES,
                'Forbidden source/archive/runtime material in package')
        require(name.startswith(BASE + '/') or name.startswith('burst_previous/'), 'Package prefix differs')
    return sorted(names), {'counts': counts,
                          'primary_scope': pin(root, primary_scope_path),
                          'context_scope': pin(root, context_scope_path),
                          'primary_receipts': receipts, 'context_receipt': pin(root, context_path),
                          'primary_QA_receipt': pin(root, primary_qa_file),
                          'context_QA_receipt': pin(root, context_qa_file),
                          'excluded_original_HDF5': [{'path': s['path'], 'bytes': s['bytes'], 'sha256': s['sha256']}
                                                      for s in context_scope['source_compacts']]}


def build(root, output, primary_qa_path, context_qa_path):
    names, admission = completed_inputs(root, primary_qa_path, context_qa_path)
    require(not output.exists() and output.suffix == '.zip', 'A fresh ZIP destination is required')
    require(not output.resolve().is_relative_to((root / BASE).resolve()), 'ZIP output must be outside project input tree')
    manifest_path = output.with_suffix('.manifest.json')
    require(not manifest_path.exists(), 'Fresh sibling manifest destination required')
    declarations = [pin(root, confined(root, name)) for name in names]
    manifest = {'schema': 'SETI_ON_BURST4_COMPLETED_PORTABLE_PACKAGE_V1',
                'status': 'COMPLETE_PRIMARY288_AUDITS1170_CONTEXT54_INDEPENDENT_QA_PASSED',
                'files': declarations, 'file_count': len(declarations),
                'uncompressed_bytes': sum(d['bytes'] for d in declarations), **admission,
                'path_layout': 'Archive members are relative to original workspace root; extract into a fresh directory.',
                'no_numerical_arrays_opened_by_packager': True,
                'original_HDF5_included': False, 'runtime_wheels_included': False,
                'historical_result_arrays_included': False,
                'portable_context_replay': 'seti_burst_on/context_qa.py; use saved16x12096 crops and16x503 profiles',
                'full_primary_QA': 'Requires original compact HDF5 at exact excluded_original_HDF5 paths; see REPLAY_README.md.',
                'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False}
    manifest_raw = (json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for declaration in declarations:
            path = confined(root, declaration['path'])
            archive.write(path, declaration['path'])
            require(pin(root, path) == declaration, 'Input changed while archiving: ' + declaration['path'])
        archive.writestr('ON_BURST4_PACKAGE_MANIFEST.json', manifest_raw)
    with zipfile.ZipFile(output, 'r') as archive:
        require(archive.testzip() is None, 'Archive CRC verification failed')
        require(set(archive.namelist()) == {*names, 'ON_BURST4_PACKAGE_MANIFEST.json'}, 'Closed archive member census differs')
    with manifest_path.open('xb') as stream:
        stream.write(manifest_raw)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': manifest['status'], 'archive_path': str(output), 'archive_bytes': output.stat().st_size,
                      'archive_sha256': digest(output), 'manifest_path': str(manifest_path),
                      'file_count': manifest['file_count'], 'counts': manifest['counts']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--preflight', action='store_true')
    mode.add_argument('--inventory', '--prepare', action='store_true')
    mode.add_argument('--build', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--primary-qa-receipt', default=BASE + '/qa_results/QA_RECEIPT.json')
    parser.add_argument('--context-qa-receipt', default=BASE + '/context_qa_results/QA_RECEIPT.json')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.preflight:
        print(json.dumps({'status': 'PASS_STATIC_PACKAGE_INTERFACE_NO_ARRAYS_OR_WRITES',
                          'packager_sha256': digest(Path(__file__)),
                          'expected_primary_maps': 288, 'expected_primary_audits': 1170,
                          'expected_context_profiles': 54, 'original_HDF5_included': False,
                          'runtime_wheels_included': False, 'numerical_modules_imported': False}))
        return
    if args.inventory:
        print(json.dumps(prospective_inventory(root)))
        return
    require(args.output is not None, '--build requires a fresh --output ZIP path')
    output = args.output if args.output.is_absolute() else root / args.output
    build(root, output.resolve(), args.primary_qa_receipt, args.context_qa_receipt)


if __name__ == '__main__':
    main()
