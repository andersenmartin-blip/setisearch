"""Metadata-only builder for the independently frozen full-source QA GO.

Check-only verifies the actual v2 public readback and synthetic PASS. Prepare
additionally requires the terminal21-shard queue PASS and21 exact COMPLETE
receipts; it creates a fresh QA_ROOT_GO but never executes numerical QA or
opens/decompresses any HDF5/NPZ value payload.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re

BASE = 'seti_burst_full'
QA_SHA = 'ccc7f96d079653d04df5a679af2192173a8e1281c80a3d21b995d5a3dd847cd5'
TEST_SHA = '832d3adb826b9b354bd0d1aefa8132d31e9e92deece2af36c96b2bbaeba11bc0'
SCOPE_SHA = 'd8944b1a8959c945cc5179c7bc1b3677d5aba4352d8e7529e72dce64c66a2ab7'
DRIVER_SHA = '6d4a0f898cbebb140844225ae8815eb52331713054d619a6f96dcf59df7ee661'
SYNTHETIC_SHA = 'b10b267069ea07c477016c0b9f1fb8911b23545b4b8e9b31cd5c79c23d67f436'
JOBS = tuple(f'full20170428_epoch{epoch}_HIP98505_shard{shard:02d}'
             for epoch in (1, 2, 3) for shard in range(7))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def confined(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts
            and path.resolve().is_relative_to(root) and not path.is_symlink(), 'Confined relative path required')
    return path


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def pin(root, path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def code_admission(root):
    own = Path(__file__).resolve()
    ast.parse(own.read_text())
    require(digest(root / BASE / 'qa_v2.py') == QA_SHA
            and digest(root / BASE / 'test_qa_synthetic_v2.py') == TEST_SHA
            and digest(root / BASE / 'SCOPE.json') == SCOPE_SHA
            and digest(root / BASE / 'driver.py') == DRIVER_SHA, 'Frozen exact source/scope hashes differ')
    freeze_path = root / BASE / 'freeze.json'
    freeze = read(freeze_path)
    require(freeze['status'] == 'PASS_PUBLIC_FREEZE_FULL_ON_DUAL_BURST4_SCOPE_READBACK'
            and freeze['scope_sha256'] == SCOPE_SHA and freeze['driver_sha256'] == DRIVER_SHA
            and freeze['new_maps_executed_yet'] == 0
            and re.fullmatch('[0-9a-f]{40}', freeze['public_commit']), 'Prospective primary freeze differs')
    for declaration in freeze['files']:
        raw = confined(root, declaration['path']).read_bytes()
        require(declaration['exact'] is True
                and hashlib.sha1(('blob %d\0' % len(raw)).encode() + raw).hexdigest() == declaration['git_blob_sha'],
                'Original served primary blob bytes changed')
    qa_freeze_path = root / BASE / 'QA_V2_FREEZE.json'
    qa_freeze = read(qa_freeze_path)
    require(qa_freeze['status'] == 'PASS_PUBLIC_FREEZE_QA_V2_SOURCE_ONLY_READBACK'
            and qa_freeze['primary_public_commit'] == freeze['public_commit']
            and re.fullmatch('[0-9a-f]{40}', qa_freeze['public_commit'])
            and qa_freeze['synthetic_values_executed_before_freeze'] is False
            and qa_freeze['source_values_read_before_freeze'] is False, 'Prospective v2 QA freeze differs')
    declared_paths = set()
    for declaration in qa_freeze['files']:
        path = confined(root, declaration['local'])
        require(declaration['local'] not in declared_paths, 'Duplicate v2 public-readback file')
        declared_paths.add(declaration['local'])
        actual = pin(root, path)
        raw = path.read_bytes()
        require(actual['bytes'] == declaration['bytes'] and actual['sha256'] == declaration['sha256']
                and hashlib.sha1(('blob %d\0' % len(raw)).encode() + raw).hexdigest() == declaration['gitsha'],
                'V2 served public file bytes differ')
    require(declared_paths == {BASE + '/qa_v2.py', BASE + '/test_qa_synthetic_v2.py', BASE + '/QA_V2_SCIENCE_STATIC_REVIEW.json'},
            'Exact3 v2 readback files required')
    synthetic_go_path = root / BASE / 'SYNTHETIC_V2_GO.json'
    synthetic_go = read(synthetic_go_path)
    synthetic_path = root / BASE / 'SYNTHETIC_V2_RECEIPT.json'
    require(digest(synthetic_path) == SYNTHETIC_SHA, 'Exact synthetic PASS receipt differs')
    synthetic = read(synthetic_path)
    require(synthetic_go['status'] == 'GO_FULL_DUAL_QA_SYNTHETIC_TESTS'
            and synthetic_go['qa_sha256'] == QA_SHA and synthetic_go['test_sha256'] == TEST_SHA
            and synthetic_go['public_commit'] == qa_freeze['public_commit']
            and synthetic['status'] == 'PASS_INDEPENDENT_DUAL_MAX_SYNTHETIC_REGRESSIONS'
            and synthetic['qa_sha256'] == QA_SHA and synthetic['test_sha256'] == TEST_SHA
            and synthetic['root_go_sha256'] == digest(synthetic_go_path)
            and synthetic['public_commit'] == qa_freeze['public_commit']
            and synthetic['source_values_read'] is False and synthetic['numerical_tests_executed'] is True
            and len(synthetic['cases']) == 10 and all(case['status'] == 'PASS' for case in synthetic['cases']),
            'Actual synthetic GO/PASS evidence differs')
    scope, primary_go_path = read(root / BASE / 'SCOPE.json'), root / BASE / 'ROOT_GO.json'
    primary_go = read(primary_go_path)
    require(primary_go['status'] == 'GO_2010_NEW_FULL_ON_DUAL_BURST4_MAPS'
            and primary_go['scope_sha256'] == SCOPE_SHA and primary_go['driver_sha256'] == DRIVER_SHA
            and primary_go['freeze_sha256'] == digest(freeze_path)
            and set(scope['jobs']) == set(JOBS), 'Original producer admission differs')
    go = {'status': 'GO_INDEPENDENT_FULL_ON_DUAL_BURST4_QA',
          'scope_sha256': SCOPE_SHA, 'qa_sha256': QA_SHA, 'driver_sha256': DRIVER_SHA,
          'primary_public_freeze_commit': freeze['public_commit'],
          'qa_public_freeze_commit': qa_freeze['public_commit'],
          'primary_admission_pins': {BASE + '/ROOT_GO.json': pin(root, primary_go_path),
                                     BASE + '/freeze.json': pin(root, freeze_path)},
          'QA_v2_public_readback_pin': pin(root, qa_freeze_path),
          'synthetic_receipt_pin': pin(root, synthetic_path),
          'synthetic_test_path': BASE + '/test_qa_synthetic_v2.py',
          'synthetic_test_sha256': TEST_SHA, 'synthetic_root_GO_pin': pin(root, synthetic_go_path),
          'CPU_cap_s': 600, 'wall_cap_s': 900, 'memory_cap_bytes': 2 * 1024**3,
          'output_cap_bytes': 8 * 1024**2, 'builder_code_pin': pin(root, own),
          'source_values_opened_by_builder': False, 'QA_numerical_execution_started_by_builder': False}
    return scope, go


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-only', action='store_true')
    mode.add_argument('--prepare', action='store_true')
    parser.add_argument('--output', default=BASE + '/QA_ROOT_GO.json')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    scope, go = code_admission(root)
    if args.check_only:
        print(json.dumps({'status': 'PASS_METADATA_ONLY_EXACT_V2_SYNTHETIC_PUBLIC_ADMISSION',
                          'qa_sha256': QA_SHA, 'test_sha256': TEST_SHA,
                          'synthetic_receipt_pin': go['synthetic_receipt_pin'],
                          'primary_public_freeze_commit': go['primary_public_freeze_commit'],
                          'qa_public_freeze_commit': go['qa_public_freeze_commit'],
                          'expected_producer_receipts': 21, 'source_values_read': False,
                          'QA_execution_started': False}))
        return
    queue_path = root / BASE / 'QUEUE_RECEIPT.json'
    queue = read(queue_path)
    require(queue['status'] == 'PASS_ALL21_SHARDS2010_NEW_MAPS' and queue['maps'] == 2010
            and queue['max_concurrent'] == 2 and queue['automatic_retries'] == 0
            and len(queue['jobs']) == 21 and {r['job'] for r in queue['jobs']} == set(JOBS)
            and all(r['status'] == 'COMPLETE' for r in queue['jobs']), 'Terminal complete21-shard queue PASS required')
    queued = {record['job']: record for record in queue['jobs']}
    declared, maps = {}, 0
    for job in JOBS:
        path = root / BASE / 'results' / job / 'EXECUTION_RECEIPT.json'
        receipt = read(path)
        current = digest(path)
        require(receipt['status'] == 'COMPLETE_NEW_FULL_ON_DUAL_BURST4_SHARD_EXPLORATORY_ONLY'
                and receipt['primary_id'] == job and receipt['scope_sha256'] == SCOPE_SHA
                and receipt['driver_sha256'] == DRIVER_SHA
                and receipt['counts'] == scope['jobs'][job]['expected_counts']
                and receipt['scan_id'] == scope['jobs'][job]['scan_id']
                and receipt['original_acquisition_role'] == 'ON'
                and receipt['decoded_row_SHA_checks_before'] == receipt['decoded_row_SHA_checks_after'] == 48
                and receipt['source_bytes_unchanged'] is True
                and receipt['public_freeze_commit'] == go['primary_public_freeze_commit']
                and receipt['root_GO_pin'] == go['primary_admission_pins'][BASE + '/ROOT_GO.json']
                and receipt['public_freeze_pin'] == go['primary_admission_pins'][BASE + '/freeze.json']
                and queued[job]['receipt_sha256'] == current
                and queued[job]['maps'] == receipt['counts']['maps'], 'Exact completed producer/queue receipt differs: ' + job)
        declared[job] = current
        maps += receipt['counts']['maps']
    require(maps == 2010, 'Exact2010 completed dual maps required')
    go['primary_receipt_sha256s'] = declared
    go['queue_PASS_pin'] = pin(root, queue_path)
    path = confined(root, args.output)
    with path.open('xb') as stream:
        stream.write((json.dumps(go, indent=2, sort_keys=True, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': 'PREPARED_ROOT_QA_GO_FROM21_COMPLETE_FROZEN_SHARDS',
                      'root_go_pin': pin(root, path), 'producer_receipts': 21, 'completed_maps': maps,
                      'source_values_read': False, 'QA_execution_started': False}))


if __name__ == '__main__':
    main()
