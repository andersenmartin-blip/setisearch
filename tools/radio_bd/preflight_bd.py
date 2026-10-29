"""Offline BC-to-BD recovery preflight. Python standard library only; no transport.

Reproduces byte integrity against the published BC checkpoint. This does not
independently validate the inherited codec, TREE traversal or scientific search.
Only declared acquired NPY rows receive per-row checks; padding is never data.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct

INVENTORY_SHA256 = '53b1a64adf2caeccad70f7b40e45bca148ea46b4ad598cca4ed02d75c1710e50'
PROOF_SHA256 = '44e0ece723e7908f072dc5b5fc763a811793134df45412ee4e19fe2e4597777a'
SPEC_PATH = 'work_bc/science_handoff/NEXT_EIGHT_ROW_RECOVERY_SPEC_BC.json'
ARRAY_PATH = 'work_bc/acquire/data/scan5.npy.partial'


class InvalidCheckpoint(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidCheckpoint(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_path(root, relative):
    rel = Path(relative)
    require(not rel.is_absolute() and '..' not in rel.parts, 'Unsafe checkpoint path')
    result = root / rel
    require(result.resolve().is_relative_to(root.resolve()), 'Checkpoint path escapes root')
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def verify_inventory(root):
    path = root / 'INVENTORY_BC.json'
    require(digest(path) == INVENTORY_SHA256, 'BC inventory hash differs')
    entries = read_json(path)['members']
    require(len({e['path'] for e in entries}) == len(entries), 'Duplicate inventory paths')
    total = 0
    for entry in entries:
        p = safe_path(root, entry['path'])
        require(p.is_file() and not p.is_symlink(), 'Missing or linked member: ' + entry['path'])
        require(p.stat().st_size == entry['bytes'], 'Member length differs: ' + entry['path'])
        require(digest(p) == entry['sha256'], 'Member hash differs: ' + entry['path'])
        total += entry['bytes']
    return {'members_verified': len(entries), 'bytes_verified': total,
            'inventory_sha256': INVENTORY_SHA256}


def verify_valid_rows(path, reports, combined_sha256):
    """Parse the fixed NPY storage header without NumPy or any float decoding."""
    require([r['time_index'] for r in reports] == list(range(8)), 'Expected eight acquired rows')
    with Path(path).open('rb') as stream:
        require(stream.read(8) == b'\x93NUMPY\x01\x00', 'Expected retained NPY v1.0')
        raw_length = stream.read(2)
        require(len(raw_length) == 2, 'Truncated NPY header length')
        length = struct.unpack('<H', raw_length)[0]
        require(0 < length <= 4096, 'Unexpected NPY header size')
        header_bytes = stream.read(length)
        require(len(header_bytes) == length, 'Truncated NPY header')
        try:
            header = ast.literal_eval(header_bytes.decode('latin1').strip())
        except (ValueError, SyntaxError) as exc:
            raise InvalidCheckpoint('Malformed NPY header') from exc
        require(header == {'descr': '<f4', 'fortran_order': False, 'shape': (16, 1048576)},
                'Unexpected NPY storage layout')
        offset = stream.tell()
        require(offset % 16 == 0, 'Unaligned NPY payload')
        row_bytes = 1048576 * 4
        require(Path(path).stat().st_size == offset + 16 * row_bytes, 'NPY file length differs')
        combined = hashlib.sha256()
        result = []
        for report in reports:
            raw = stream.read(row_bytes)
            require(len(raw) == row_bytes, 'Truncated acquired row')
            row_hash = hashlib.sha256(raw).hexdigest()
            require(row_hash == report['decoded_row_sha256'],
                    'Acquired row bytes differ: ' + str(report['time_index']))
            combined.update(raw)
            result.append({'time_index': report['time_index'], 'sha256': row_hash})
        require(combined.hexdigest() == combined_sha256, 'Combined valid-row hash differs')
        require(stream.tell() == offset + 8 * row_bytes, 'Read outside acquired rows')
    return {'header_bytes': offset, 'per_row_bytes': row_bytes, 'checked_rows': result,
            'acquired_payload_bytes_checked': 8 * row_bytes,
            'combined_sha256': combined.hexdigest(), 'unacquired_rows_interpreted': 0,
            'codec_decodes_executed': 0}


def transition_plan(spec, summary):
    state = spec['existing_read_state']
    require(spec['target'] == summary['target'] == 'HIP44295', 'Wrong target')
    require(spec['primary_id'] == summary['primary_id'] == 65133, 'Wrong queue head')
    require(state['original_BB_decoded_rows'] == summary['inherited_BB_decoded_rows'] == 87,
            'BB lineage differs')
    require(state['BC_new_decoded_rows'] == summary['new_BC_decoded_rows'] == 1,
            'BC lineage differs')
    require(state['total_previously_decoded_rows'] == summary['validated_native_rows'] == 88,
            'Expected 88 prior rows')
    require(state['latest_valid_partial_time_rows'] == summary['scan5_valid_partial_row_indices']
            == list(range(8)), 'Stale partial-row state')
    require(state['remaining_unacquired_time_rows'] == summary['scan5_unacquired_row_indices']
            == list(range(8, 16)), 'Only eight rows remain')
    require(state['prior_BB_repeat_checks'] == summary['verified_repeat_checks'] == 5
            and state['new_BC_repeat_checks'] == summary['new_BC_repeat_checks'] == 0,
            'Repeat lineage differs')
    require(state['remaining_repeat_scan'] == 5 and state['remaining_repeat_time_row'] == 7
            and summary['remaining_repeat_checks'] == 1, 'Wrong remaining repeat')
    require(spec['scientific_baseline']['unique_archive_ids'] == summary['credited_unique_archive_ids'] == 486
            and spec['scientific_baseline']['technical_MHz_visits']
            == summary['credited_technical_MHz_visits'] == 268.50128173828125,
            'Completed baseline differs')
    require(spec['network_requests_authorized_by_this_document'] == 0
            and summary['network_release_authorized'] is False, 'Unexpected inherited network release')
    failed = spec['exact_failed_request']
    require((failed['archive_id'], failed['scan'], failed['start'], failed['stop_inclusive'],
             failed['bytes'], failed['received_bytes']) == (65143, 5, 9241886720, 9241903103, 16384, 0),
            'Pending metadata request differs')
    require(failed['start'] == summary['failed_request']['start']
            and failed['stop_inclusive'] == summary['failed_request']['stop_inclusive'],
            'Failure/spec interval mismatch')
    return {
        'schema': 'SETI_BD_MISSING_ONLY_PLAN_V1', 'status': 'OFFLINE_PLAN_NO_NETWORK_RELEASE',
        'target': 'HIP44295', 'primary_id': 65133,
        'row_lineage': {'BB_prior': 87, 'BC_prior': 1, 'BD_acquired': 0,
                        'later_missing': 8, 'expected_total': 96},
        'resume_scan5_time_indices': list(range(8, 16)),
        'repeat_lineage': {'prior': 5, 'BD_new': 0, 'later_missing': 1},
        'pending_repeat': {'scan': 5, 'time_index': 7, 'must_be_genuine_new_http_receipt': True},
        'first_pending_metadata_request': failed,
        'unknown_row8_payload_extent': True,
        'first_pending_request_is_payload': False,
        'no_automatic_retry': True, 'no_alternate_endpoint': True,
        'network_requests_authorized': 0, 'detector_runs_authorized': 0,
        'old_BC_nine_row_runner_reusable_as_is': False,
        'requirements': [
            'Normal archive access must be available; this plan does not grant it.',
            'Restore and verify all BB parent arrays, receipts, TREE cache, source and prior proof.',
            'Implement and review a new 88+8 runner and 5+1 repeat proof before dispatch.',
            'Preserve all old failed attempts, partial arrays and prefix/tail source lineage.',
            'Request only missing verified extents after deriving genuine TREE descriptors.',
            'Require native completion, unchanged detector/triage/review gates before coverage credit.'
        ]}


def preflight(root):
    root = Path(root).resolve()
    inventory = verify_inventory(root)
    proof_path = root / 'work_bc/review/PARTIAL_INPUT_PROOF_BC.json'
    require(digest(proof_path) == PROOF_SHA256, 'BC proof hash differs')
    proof, spec = read_json(proof_path), read_json(root / SPEC_PATH)
    summary = proof['partial_summary']
    require(proof['science_completed'] is False and proof['detector_searches_executed'] == 0,
            'Unexpected completed science')
    rows = verify_valid_rows(root / ARRAY_PATH, proof['scan5_valid_row_reports'],
                             summary['scan5_valid_rows_power_sha256'])
    plan = transition_plan(spec, summary)
    actual = read_json(root / 'work_bc/execution/RECOVERY_ACTUAL_EXIT_BC.json')
    require(actual['actual_exit_code'] == 1 and actual['stdout_eof']
            and actual['child_wait_completed'], 'BC failed execution was success-aliased')
    log = root / 'work_bc/execution/RECOVERY.log'
    require(digest(log) == actual['log_sha256'] and log.stat().st_size == actual['log_bytes'],
            'BC recovery log differs')
    failure = read_json(root / 'work_bc/NETWORK_FAILURE_RECOVERY_BC.json')
    require(failure['partial_bytes'] == 0 and failure['attempts'] == 1
            and failure['automatic_retry'] is False, 'Failure accounting differs')
    derived_path = root / 'work_bc/acquire/derived/scan5_row7.bin'
    derived = read_json(derived_path.with_suffix('.json'))
    prefix_path = root / 'work_bc/acquire/transport/scan5_8154457534_8157560831.bin'
    prefix = prefix_path.read_bytes()
    raw = derived_path.read_bytes()
    require(raw[:len(prefix)] == prefix and len(raw) - len(prefix) == 13580,
            'Row7 derived prefix/tail lengths differ')
    require(derived['new_HTTP_whole_chunk_receipt_claimed'] is False,
            'Derived chunk is not a whole-chunk HTTP receipt')
    retained = read_json(root / 'work_bc/science_handoff/PARTIAL_RETENTION_INVENTORY_BC.json')
    canonical = []
    for entry in retained['canonical_arrays']:
        p = safe_path(root, entry['path'])
        local = p.is_file()
        if local:
            require(p.stat().st_size == entry['bytes'] and digest(p) == entry['sha256'],
                    'Parent canonical array differs')
        canonical.append({**entry, 'verified_locally_this_run': local})
    return {
        'schema': 'SETI_BD_OFFLINE_PREFLIGHT_RESULT_V1',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'PASS_BC_BYTES_ONLY_FULL_RECOVERY_BLOCKED',
        'inventory': inventory, 'independent_stdlib_row_storage_check': rows,
        'source_sha256': digest(__file__), 'BC_proof_sha256': PROOF_SHA256,
        'BC_spec_sha256': digest(root / SPEC_PATH), 'plan': plan,
        'parent_canonical_arrays': canonical,
        'parent_arrays_verified_locally': sum(e['verified_locally_this_run'] for e in canonical),
        'old_BC_failed_actual_exit_preserved': 1,
        'row7_prefix_bytes_compared': len(prefix), 'row7_inherited_tail_bytes': 13580,
        'row7_parent_tail_receipt_independently_rehydrated': False,
        'archive_requests_this_run': 0, 'new_observational_rows': 0,
        'detector_searches_executed': 0, 'candidate_assessment': None,
        'new_unique_archive_ids': 0, 'new_technical_MHz_visits': 0,
        'completed_science_authority_stage': 'BA', 'queue_advanced': False,
        'science_completed': False,
        'limitations': [
            'BC package bytes and valid row hashes checked against inherited pinned proof.',
            'Parent BB arrays and TREE/receipt cache remain referenced; not all rehydrated here.',
            'No independent codec decode, native HDF traversal, detector run or astronomical qualification.',
            'Current environment restricts network destinations; archive host is not in its allowlist.',
            'No archive probe, retry or alternative route performed.'
        ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = preflight(args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'members_verified': result['inventory']['members_verified'],
                      'valid_rows_checked': 8, 'archive_requests': 0, 'science_completed': False}))


if __name__ == '__main__':
    main()
