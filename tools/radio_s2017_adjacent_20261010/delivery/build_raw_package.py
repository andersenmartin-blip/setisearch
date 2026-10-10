"""Create/verify new170/172 RAW archive only after actual source QA and root GO.

Never deletes sidecars, acquires data, decodes power or claims remote persistence.
"""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import re
import signal
import time
import archive_common as common
from reconstruct_raw_sidecars import MANIFEST, MANIFEST_SHA, STAGE, contract, verify_compacts

PHASE = Path('analysis/s2017_next_native')
DELIVERY = PHASE / 'delivery'
SCOPE = DELIVERY / 'RAW_DELIVERY_SCOPE.json'
QA = PHASE / 'results/source_review/QA_RECEIPT.json'
QA_STATUS = 'PASS_ADJACENT170_172_12_COMPACTS192_COMPRESSED_CHUNKS192_DECODED_ROWS_AND_SOURCE_RANGE_PROVENANCE'
QA_COUNTS = {'native_chunks': 2, 'compact_files': 12, 'source_headers': 12,
             'source_descriptors': 192, 'exact_range_records': 192,
             'unique_source_ranges': 192, 'durable_raw_sidecars': 192,
             'compressed_source_chunks': 192, 'decoded_rows': 192}


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'expected-scope-sha256', 'acquisition-sha256', 'source-qa-sha256', 'freeze-commit'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--root-go-after-source-qa', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    for value in (args.expected_scope_sha256, args.acquisition_sha256, args.source_qa_sha256):
        common.require(re.fullmatch('[0-9a-f]{64}', value), 'Actual SHA256 argument required')
    common.require(re.fullmatch('[0-9a-f]{40}', args.freeze_commit), 'Actual public40-hex delivery freeze required')
    common.require(args.root_go_after_source_qa, 'Explicit root GO after actual source QA required')
    common.require(common.digest(root / SCOPE) == args.expected_scope_sha256, 'Delivery scope pin differs')
    scope = json.loads((root / SCOPE).read_bytes())
    common.require(scope['schema'] == 'SETI_ADJACENT170_172_RAW_DELIVERY_SCOPE_V1' and
                   scope['source_manifest_sha256'] == MANIFEST_SHA and
                   scope['workspace_cap_bytes'] == common.CAP and
                   scope['CPU_cap_s'] == common.CPU_CAP and scope['wall_cap_s'] == common.WALL_CAP and
                   scope['memory_cap_bytes'] == common.MEMORY_CAP, 'Frozen delivery contract differs')
    for relative, expected in scope['code_and_metadata_pins'].items():
        common.require(common.pin(root, relative) == {'path': relative, **expected}, 'Builder/metadata code pin differs')
    common.require(common.digest(root / QA) == args.source_qa_sha256, 'Actual source QA receipt pin differs')
    qa = json.loads((root / QA).read_bytes())
    common.require(qa['schema'] == 'SETI_S2017_ADJACENT170_172_COMPACT_SOURCE_QA_V1' and
                   qa['status'] == QA_STATUS and qa['counts'] == QA_COUNTS and
                   qa['acquisition_receipt_sha256'] == args.acquisition_sha256 and
                   qa['source_manifest_sha256'] == MANIFEST_SHA and
                   qa['qa_script_sha256'] == common.digest(root / PHASE / 'qa_sources.py') and
                   qa['new_telescope_HTTP_requests'] == qa['new_telescope_BODY_bytes'] == 0 and
                   qa['detector_or_score_rerun'] is False and qa['medians_recomputed'] is False,
                   'Actual source QA admission differs')
    acquisition, manifest = contract(root, args.acquisition_sha256)
    common.require(qa['scope_sha256'] == acquisition['scope_sha256'] and
                   qa['driver_sha256'] == acquisition['driver_sha256'] and
                   qa['public_freeze_commit'] == acquisition['public_freeze_commit'],
                   'Source QA acquisition code/scope/freeze binding differs')
    for qa_field, acquisition_field in (
            ('source_range_raw_record_sha256', 'raw_range_records'),
            ('decoded_file_row_record_sha256', 'decoded_files'),
            ('source_range_request_record_sha256', 'value_read_requests')):
        raw = json.dumps(acquisition[acquisition_field], sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode('utf8')
        common.require(hashlib.sha256(raw).hexdigest() == qa[qa_field],
                       'Actual source QA canonical record binding differs')
    expected_compact_pins = {(STAGE / x['array_file']).as_posix():
                             {'bytes': x['bytes'], 'sha256': x['file_sha256']}
                             for x in acquisition['decoded_files']}
    common.require(qa['compact_input_byte_pins'] == expected_compact_pins,
                   'Actual source QA12compact pins differ')
    locks = []
    common.limits(started)
    try:
        # Same acquisition family lock plus independent archive lock. Lock-file
        # existence is irrelevant; only a retained kernel flock grants admission.
        for relative in (PHASE / 'ACTIVE_FAMILY_FLOCK.lock', DELIVERY / 'ARCHIVE_ACTIVE_FLOCK.lock'):
            handle = (root / relative).open('a+')
            locks.append(handle)
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        records = verify_compacts(root, args.acquisition_sha256, require_sidecars=True)
        payload = set()
        allowed = {'.py', '.json', '.md', '.txt', '.csv', '.log'}
        for path in (root / PHASE).rglob('*'):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if '__pycache__' in relative.parts or 'packages' in relative.parts:
                continue
            if path.suffix in allowed:
                payload.add(relative.as_posix())
        compact_paths = [(STAGE / x['array_file']).as_posix() for x in acquisition['decoded_files']]
        payload.update(compact_paths)
        for relative, expected in manifest['code_and_metadata_pins'].items():
            common.require(Path(relative).suffix not in ('.h5', '.npz', '.whl', '.zip'),
                           'Only retained source metadata/code pins may be copied')
            common.require(common.pin(root, relative) == {'path': relative, **expected},
                           'Retained source metadata/code pin differs')
            payload.add(relative)
        common.require(len(compact_paths) == 12 and
                       len([x for x in payload if x.endswith('.h5')]) == 12 and
                       all('raw_ranges/' not in x for x in payload), 'RAW payload scope differs')
        context = {'scope_sha256': args.expected_scope_sha256,
                   'public_freeze_commit': args.freeze_commit,
                   'acquisition_receipt_sha256': args.acquisition_sha256,
                   'source_QA_receipt_sha256': args.source_qa_sha256,
                   'source_manifest_sha256': MANIFEST_SHA,
                   'compact_files': 12, 'compressed_H5_chunks_verified': 192,
                   'decoded_power_rows_by_builder': 0,
                   'native171_H5_copied': False, 'raw_sidecars_copied': False,
                   'sidecar_reconstruction_helper': (DELIVERY / 'reconstruct_raw_sidecars.py').as_posix(),
                   'root_only_sidecar_removal_requires_confirmed_remote_save': True}
        receipt = common.assemble(root, root / DELIVERY / 'packages/raw',
                                  scope['archive_filename'], payload, 'RAW', context, started)
        # Confirm gates remain exact after copying and every-member verification.
        common.require(common.digest(root / QA) == args.source_qa_sha256 and
                       common.digest(root / STAGE / 'ACQUISITION_RESULT.json') == args.acquisition_sha256 and
                       common.digest(root / SCOPE) == args.expected_scope_sha256,
                       'Archive admission receipt changed')
        common.save_new(root / DELIVERY / 'RAW_PACKAGE_RECEIPT.json', receipt)
        common.save_new(root / DELIVERY / 'SIDECAR_RETENTION_CANDIDATES.json', {
            'status': 'CANDIDATES_ONLY_NO_DELETION_AUTHORIZED_BY_BUILDER',
            'raw_archive_sha256': receipt['archive_sha256'],
            'public_freeze_commit': args.freeze_commit,
            'raw_package_receipt_sha256': common.digest(root / DELIVERY / 'RAW_PACKAGE_RECEIPT.json'),
            'acquisition_receipt_sha256': args.acquisition_sha256,
            'source_QA_receipt_sha256': args.source_qa_sha256,
            'compressed_H5_chunks_reverified': 192,
            'remote_save_confirmed_by_builder': False,
            'root_must_confirm_durable_save_before_removal': True,
            'sidecar_count': 192, 'sidecar_bytes': sum(x['bytes'] for x in records), 'files': records})
        print(json.dumps(receipt), flush=True)
    finally:
        signal.alarm(0)
        for handle in reversed(locks):
            handle.close()


if __name__ == '__main__':
    main()
