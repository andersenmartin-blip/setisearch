"""Package closed BO engineering evidence without importing or decoding arrays.

This post-execution transport/audit helper is outside the preregistered detector
sources. It never modifies the work_bo tree, retries gates, opens astronomical
data, imports NumPy, or changes a historical result. Every ZIP and receipt is
created exclusively; interrupted or invalid packages remain visibly partial.
The ZIP contains binary outputs, typed special-node/directory evidence and
generated resume/manifest metadata only. UTF-8 repository text/code is checked
and referenced by hashes and GitHub paths; its contents are never embedded.
"""
from __future__ import annotations

import argparse
import codecs
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import zipfile

HERE = Path(__file__).resolve().parent
WORK = HERE / 'setisearch/work_bo'
SHA256 = re.compile(r'[0-9a-f]{64}\Z')
CHUNK = 1024 * 1024
MAX_PART_BYTES = 200 * 1024 * 1024
REPOSITORY = 'andersenmartin-blip/setisearch'
BRANCH = 'm43-support-qualification'
BINARY_SUFFIXES = {'.npy', '.npz', '.zip', '.bin'}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def is_utf8_file(path):
    """Classify bytes only; no arrays, archives or source code are executed."""
    decoder = codecs.getincrementaldecoder('utf-8')('strict')
    try:
        with path.open('rb') as stream:
            while True:
                block = stream.read(CHUNK)
                if not block:
                    break
                decoder.decode(block, final=False)
        decoder.decode(b'', final=True)
    except UnicodeError:
        return False
    return True


def write_json_exclusive(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def identity(path):
    info = path.lstat()
    admitted = (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)
                or stat.S_ISLNK(info.st_mode) or stat.S_ISFIFO(info.st_mode))
    require(admitted, 'Unsupported evidence node: ' + str(path))
    if not stat.S_ISREG(info.st_mode) and not stat.S_ISDIR(info.st_mode):
        relative = path.relative_to(WORK).as_posix()
        allowed = {
            'execution/BO_ENGINEERING_V1/E01/payload/fixtures/symlink.npy',
            'execution/BO_ENGINEERING_V1/E01/payload/fixtures/nonblocking_fifo.npy',
        }
        require(relative in allowed,
                'Special node is not a declared E01 rejection fixture: ' + str(path))
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_mode)


def node_payload(path):
    """Only special-node metadata payloads; never open a FIFO or link target."""
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode):
        return os.fsencode(os.readlink(path))
    if stat.S_ISFIFO(mode) or stat.S_ISDIR(mode):
        return b''
    raise ValueError('Regular file is streamed separately')


def describe_node(path):
    info = path.lstat()
    if stat.S_ISREG(info.st_mode):
        return {'node_type': 'regular', 'bytes': info.st_size, 'sha256': sha(path)}
    payload = node_payload(path)
    result = {'node_type': ('symlink' if stat.S_ISLNK(info.st_mode) else
                            'fifo' if stat.S_ISFIFO(info.st_mode) else 'directory'),
              'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
              'lstat_size': info.st_size, 'unix_st_mode': info.st_mode,
              'node_payload_is_metadata_only': True}
    if stat.S_ISLNK(info.st_mode):
        result['link_target'] = os.readlink(path)
        result['declared_fixture_metadata_match'] = result['link_target'] == 'small_v1.npy'
    elif stat.S_ISFIFO(info.st_mode):
        result['declared_fixture_metadata_match'] = stat.S_IMODE(info.st_mode) == 0o600 and info.st_size == 0
    return result


def safe_work_path(value):
    path = Path(value)
    if not path.is_absolute():
        path = WORK / path
    resolved = path.resolve(strict=True)
    require(resolved.is_relative_to(WORK.resolve()), 'Evidence path escapes work_bo: ' + str(value))
    # Reject a symlink at any level inside the evidence root.
    current = WORK
    for part in path.absolute().relative_to(WORK.absolute()).parts:
        current = current / part
        require(not current.is_symlink(), 'Symlink evidence path rejected: ' + str(current))
    require(path.absolute() == resolved, 'Noncanonical evidence path: ' + str(value))
    return resolved


def inventory():
    paths = []
    for path in sorted(WORK.rglob('*')):
        if '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        identity(path)
        paths.append(path)
    return paths


def verify_source_pins(plan):
    rows = plan.get('source_pins')
    require(isinstance(rows, list) and rows, 'Nonempty frozen source pin list required')
    seen = set()
    for row in rows:
        relative = Path(row['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'Invalid source-relative path')
        require(relative.as_posix() not in seen, 'Repeated source pin')
        seen.add(relative.as_posix())
        require(type(row['bytes']) is int and row['bytes'] >= 0, 'Invalid source byte count')
        require(isinstance(row['sha256'], str) and SHA256.fullmatch(row['sha256']), 'Invalid source hash')
        path = safe_work_path(relative)
        require(stat.S_ISREG(path.lstat().st_mode), 'Source pins must bind regular files')
        require(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], 'Frozen source changed: ' + row['path'])
    return len(rows)


def validate_terminal(marker_path):
    """Validate actual closed outer gates, including a preserved stopped prefix.

    E05 deliberately contains failing software children. Those artifacts are
    retained verbatim; only the outer gate has the normal PASS contract.
    """
    plan_path = WORK / 'BO_ENGINEERING_PLAN.json'
    plan = read_json(plan_path)
    root = safe_work_path(plan['execution_relative_dir'])
    require(marker_path.parent == root and marker_path.name in {'RUN_COMPLETE_BO.json', 'RUN_STOP_BO.json'},
            'Not a recognized BO terminal location')
    alternate = root / ('RUN_STOP_BO.json' if marker_path.name == 'RUN_COMPLETE_BO.json' else 'RUN_COMPLETE_BO.json')
    require(not alternate.exists(), 'Conflicting complete and stop terminal markers')
    marker = read_json(marker_path)
    require(marker['schema'] == 'SETI_BO_ENGINEERING_TERMINAL_V1', 'Wrong terminal schema')
    require(marker['engineering_only'] is True and marker['background_children_running'] is False,
            'Engineering must be terminal with no background child')
    require(marker.get('special_node_scope_status') == 'PASS_EXACT_DECLARED_OR_FAILED_PREFIX_SUBSET',
            'Unexpected/changed special-node scope requires separate parent-authorized forensics')
    require(marker['plan_sha256'] == sha(plan_path), 'Terminal plan hash differs')
    freeze_path = WORK / 'PUBLIC_FREEZE_RECEIPT_BO.json'
    freeze = read_json(freeze_path)
    require(freeze['schema'] == 'SETI_BO_PUBLIC_FREEZE_RECEIPT_V1'
            and freeze['exact_readback_verified'] is True and freeze['before_execution'] is True,
            'Missing exact public preregistration readback')
    require(freeze['plan_sha256'] == marker['plan_sha256']
            and freeze['public_commit_sha'] == marker['prereg_public_commit_sha'],
            'Public preregistration differs from terminal')
    require(re.fullmatch('[0-9a-f]{40}', marker['prereg_public_commit_sha']) is not None,
            'Invalid public commit hash')
    expected_ids = [row['id'] for row in plan['gates']]
    require(expected_ids == ['E01', 'E02', 'E03', 'E04', 'E05'], 'Wrong ordered engineering gates')
    receipt_rows = marker['gate_receipts']
    require(isinstance(receipt_rows, list) and len(receipt_rows) <= 5, 'Wrong outer receipt count')
    require([row['gate_id'] for row in receipt_rows] == expected_ids[:len(receipt_rows)],
            'Receipt gates are not the once-only ordered prefix')
    artifact_map = marker['output_artifact_sha256']
    require(isinstance(artifact_map, dict), 'Terminal artifact digest map required')
    pinned_paths = {}
    for value, digest in artifact_map.items():
        require(isinstance(digest, str) and SHA256.fullmatch(digest), 'Invalid terminal artifact digest')
        path = safe_work_path(value)
        require(path.is_relative_to(root), 'Terminal artifact escapes reserved execution root')
        require(sha(path) == digest, 'Closed output changed: ' + value)
        pinned_paths[str(path)] = digest
    special_rows = marker.get('special_node_evidence', {})
    require(isinstance(special_rows, dict), 'Typed special-node evidence map required')
    special_paths = set()
    for value, row in special_rows.items():
        path = Path(value)
        require(path.is_absolute() and '..' not in path.parts and path.is_relative_to(root),
                'Special-node path escapes reserved root')
        identity(path)  # Restricts this to the two explicitly declared E01 fixtures.
        descriptor = describe_node(path)
        require(row['type'] == descriptor['node_type'] and row['lstat_mode'] == path.lstat().st_mode
                and row['lstat_size'] == path.lstat().st_size, 'Special-node metadata changed')
        if row['type'] == 'symlink':
            require(row['target_text'] == descriptor['link_target']
                    and row['target_sha256'] == descriptor['sha256'], 'Symlink target metadata changed')
        require(str(path) not in pinned_paths, 'Special node also appears in regular byte hash map')
        special_paths.add(str(path))
    actual_receipts = []
    successful = []
    all_eof = True
    for row in receipt_rows:
        gate_id = row['gate_id']
        path = safe_work_path(row['path'])
        require(path == root / gate_id / 'ACTUAL_RECEIPT.json', 'Wrong actual receipt location')
        require(sha(path) == row['sha256'] == pinned_paths.get(str(path)), 'Actual receipt digest mismatch')
        receipt = read_json(path)
        require(receipt['schema'] == 'SETI_BO_EXACT_CHILD_CAPTURE_V1', 'Wrong actual capture receipt schema')
        require(receipt['status'] == row['status'] and row['status'] in {'PASS', 'FAIL'}, 'Receipt status mismatch')
        started = receipt.get('child_pid') is not None
        if started:
            require(receipt['child_wait_completed'] is True and type(receipt['actual_exit_code']) is int
                    and receipt['stdout_eof'] is True,
                    'Captured child is not actually reaped with observed pipe EOF')
            require(receipt.get('descendant_cleanup_completed') is True
                    and receipt.get('remaining_live_descendants') == [],
                    'Started child has no completed descendant cleanup proof')
        else:
            require(row['status'] == 'FAIL' and receipt['actual_exit_code'] is None
                    and receipt['child_wait_completed'] is False,
                    'A non-started child must be an explicit failed capture, never actual-exit credit')
        log_path = safe_work_path(receipt['log_path'])
        require(log_path == root / gate_id / 'STDOUT.log', 'Wrong gate log location')
        require(log_path.stat().st_size == receipt['log_bytes']
                and sha(log_path) == receipt['log_sha256'] == pinned_paths.get(str(log_path)),
                'Saved stdout bytes differ from receipt')
        if receipt['stdout_fully_preserved'] is True:
            require(receipt['log_bytes'] == receipt['observed_stdout_bytes']
                    and receipt['log_sha256'] == receipt['observed_stdout_sha256'],
                    'Observed and saved complete stdout differ')
        all_eof = all_eof and receipt['stdout_eof'] is True
        if row['status'] == 'PASS':
            require(receipt['actual_exit_code'] == 0 and receipt['stdout_eof'] is True
                    and receipt['natural_stdout_eof'] is True and receipt['capture_error'] is None
                    and receipt['stdout_fully_preserved'] is True and receipt['reasons'] == []
                    and receipt.get('killed') is False
                    and receipt.get('process_namespace_mapping_verified') is True,
                    'A passing gate lacks a clean actual exit/EOF')
            require(receipt['source_pins_verified_before'] and receipt['source_pins_verified_after'],
                    'Passing child did not verify source pins')
            result_path = safe_work_path(receipt['result_path'])
            require(result_path == root / gate_id / 'payload/RESULT.json', 'Wrong gate result location')
            result_hash = sha(result_path)
            require(result_hash == receipt['result_sha256'] == pinned_paths.get(str(result_path)),
                    'Gate result bytes differ')
            result = read_json(result_path)
            require(result['status'] == 'PASS' and result['gate'] == gate_id, 'Passing gate result identity differs')
            lines = log_path.read_text().splitlines()
            require(lines and lines[-1].strip(), 'Missing final stdout terminal line')
            terminal = json.loads(lines[-1])
            require(terminal == receipt['terminal_stdout_json']
                    and terminal.get('event') == 'GATE_TERMINAL_EOF' and terminal.get('status') == 'PASS'
                    and terminal.get('result_sha256') == result_hash,
                    'Final stdout terminal/result binding differs')
            successful.append(receipt)
        actual_receipts.append({'gate_id': gate_id, 'status': row['status'], 'child_started': started,
                                'actual_exit_code': receipt['actual_exit_code'],
                                'child_wait_completed': receipt['child_wait_completed'], 'stdout_eof': receipt['stdout_eof'],
                                'receipt_sha256': row['sha256']})
    completed_ids = marker['gates_completed']
    require(isinstance(completed_ids, list) and completed_ids == expected_ids[:len(completed_ids)]
            and len(completed_ids) <= len(receipt_rows), 'Terminal engineering credit is not the ordered actual prefix')
    require(all(row['status'] == 'PASS' for row in receipt_rows[:len(completed_ids)]),
            'Credited completed gate lacks a passing actual capture')
    if marker_path.name == 'RUN_COMPLETE_BO.json':
        require(marker['status'] == 'PASS_ALL_FIVE_ENGINEERING_GATES'
                and len(completed_ids) == len(successful) == len(receipt_rows) == 5,
                'Completion does not close all five actual passing children')
        require(marker.get('stopped_gate') is None and marker.get('reason') is None,
                'Passing terminal has a stopped gate or reason')
    else:
        require(marker['status'] == 'STOPPED_NO_NEXT_GATE', 'Wrong stopped status')
        require(bool(marker.get('reason')), 'Stopped terminal must preserve a reason')
        # A final source/resource check may stop after all child gates passed.
        # Preserve that state as STOPPED; it is not overall run completion.
        require(len(completed_ids) <= 5, 'Stopped run has too many completed child gates')
        require(len(receipt_rows) in {len(completed_ids), len(completed_ids)+1},
                'Stopped run contains more than one uncredited child')
    for gate_id in expected_ids:
        gate_root = root / gate_id
        if not gate_root.exists():
            continue
        for path in gate_root.rglob('*'):
            mode = path.lstat().st_mode
            if stat.S_ISREG(mode) and '__pycache__' not in path.parts and path.suffix != '.pyc':
                require(str(path.resolve()) in pinned_paths, 'Gate evidence missing from closed artifact map: ' + str(path))
            elif stat.S_ISLNK(mode) or stat.S_ISFIFO(mode):
                require(str(path) in special_paths, 'Special fixture missing from typed closed evidence map: ' + str(path))
    return {'terminal_status': marker['status'], 'closed_actual_gate_receipts': actual_receipts,
            'completed_engineering_gate_ids': completed_ids,
            'passing_outer_gate_captures': len(successful), 'artifact_hashes_verified': len(pinned_paths),
            'typed_special_fixture_nodes_verified_without_dereference': len(special_paths),
            'all_outer_stdout_EOF_observed': all_eof,
            'public_commit_sha': marker['prereg_public_commit_sha'],
            'historical_failures_unchanged': True,
            'limited_and_full_paired_controls_not_qualified': True}


def member_digest(archive, name):
    digest = hashlib.sha256()
    count = 0
    with archive.open(name) as stream:
        while True:
            block = stream.read(CHUNK)
            if not block:
                break
            digest.update(block)
            count += len(block)
    return count, digest.hexdigest()


def concatenate_digest(paths):
    digest = hashlib.sha256()
    count = 0
    for path in paths:
        with path.open('rb') as stream:
            while True:
                block = stream.read(CHUNK)
                if not block:
                    break
                digest.update(block)
                count += len(block)
    return count, digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--closed-marker', required=True,
                        help='Actual closed BO runner terminal marker inside work_bo')
    parser.add_argument('--out', default=str(HERE / 'deliveries/SETI_BO_ENGINEERING_RESULTS_2026-10-30.zip'))
    parser.add_argument('--part-bytes', type=int, default=MAX_PART_BYTES)
    args = parser.parse_args()
    require(0 < args.part_bytes <= MAX_PART_BYTES, 'Part cap must be positive and at most 200MiB')
    marker_path = safe_work_path(args.closed_marker)
    terminal_review = validate_terminal(marker_path)
    plan_path = WORK / 'BO_ENGINEERING_PLAN.json'
    plan = read_json(plan_path)
    require(plan['schema'] == 'SETI_BO_ENGINEERING_PLAN_V1' and plan['engineering_only'] is True,
            'Only BO engineering is admitted')
    require(plan['real_telescope_powers_authorized'] is False and plan['rng_authorized'] is False
            and plan['scientific_scores_authorized'] is False, 'Wrong scope authority')
    source_count = verify_source_pins(plan)
    output = Path(args.out).absolute()
    require(output.suffix == '.zip' and not output.resolve().is_relative_to(WORK.resolve()),
            'Archive must be a ZIP outside immutable work_bo')
    output.parent.mkdir(parents=True, exist_ok=True)
    require(not output.exists(), 'Archive overwrite refused')
    manifest_path = output.with_name(output.stem + '_MANIFEST.json')
    report_path = output.with_name(output.stem + '_PACKAGING_VERIFICATION.json')
    start_path = output.with_name(output.stem + '_PACKAGING_START.json')
    for target in (manifest_path, report_path, start_path):
        require(not target.exists(), 'Packaging identity already used: ' + str(target))
    require(not list(output.parent.glob(output.name + '.part*')), 'Existing archive parts refused')
    before_paths = inventory()
    all_nodes = []
    signatures = {}
    for path in before_paths:
        before = identity(path)
        descriptor = describe_node(path)
        require(identity(path) == before, 'File changed while initial hashing: ' + str(path))
        relative = path.relative_to(WORK).as_posix()
        signatures[relative] = before
        all_nodes.append({'path': 'work_bo/' + relative + ('/' if descriptor['node_type'] == 'directory' else ''), **descriptor})
    script_bytes = Path(__file__).read_bytes()
    packaging_script_sha = hashlib.sha256(script_bytes).hexdigest()
    freeze_path = WORK / 'PUBLIC_FREEZE_RECEIPT_BO.json'
    freeze = read_json(freeze_path)
    prereg_paths = {'work_bo/' + row['path'] for row in plan['source_pins']}
    prereg_paths.add('work_bo/BO_ENGINEERING_PLAN.json')
    selected_indexes = set()
    repo_text = []
    for index, (path, row) in enumerate(zip(before_paths, all_nodes, strict=True)):
        if row['node_type'] in {'symlink', 'fifo'}:
            selected_indexes.add(index)
        elif row['node_type'] == 'regular':
            if path.suffix.lower() in BINARY_SUFFIXES or not is_utf8_file(path):
                selected_indexes.add(index)
            else:
                reference = {'repository_path': row['path'], 'bytes': row['bytes'],
                             'sha256': row['sha256'], 'content_embedded_in_binary_archive': False,
                             'git_commit_binding': ('preregistration' if row['path'] in prereg_paths
                                                    else 'external_final_results_commit')}
                if row['path'] in prereg_paths:
                    reference['immutable_url'] = ('https://github.com/' + REPOSITORY + '/blob/'
                                                  + freeze['public_commit_sha'] + '/' + row['path'])
                repo_text.append(reference)
    selected_paths = {before_paths[index] for index in selected_indexes}
    required_directories = set()
    for path in selected_paths:
        required_directories.update(parent for parent in path.parents
                                    if parent != WORK and parent.is_relative_to(WORK))
    execution_root = WORK / plan['execution_relative_dir']
    for index, (path, row) in enumerate(zip(before_paths, all_nodes, strict=True)):
        if row['node_type'] == 'directory' and (path in required_directories
                                               or path.is_relative_to(execution_root)):
            selected_indexes.add(index)
    selected = [(path, row) for index, (path, row) in enumerate(zip(before_paths, all_nodes, strict=True))
                if index in selected_indexes]
    members = [row for _, row in selected]
    require(all(row['node_type'] != 'regular' or path.suffix.lower() in BINARY_SUFFIXES
                or not is_utf8_file(path) for path, row in selected),
            'Repository-backed UTF-8 text must not be duplicated into the binary archive')
    created = datetime.now(timezone.utc).isoformat()
    prereg = {'repository': REPOSITORY, 'branch': BRANCH,
              'public_commit_sha': freeze['public_commit_sha'],
              'source_tree_sha': freeze['source_tree_sha'],
              'plan_path': 'work_bo/BO_ENGINEERING_PLAN.json', 'plan_sha256': sha(plan_path),
              'public_freeze_receipt_path': 'work_bo/PUBLIC_FREEZE_RECEIPT_BO.json',
              'public_freeze_receipt_sha256': sha(freeze_path)}
    resume = {
        'schema': 'SETI_BO_BINARY_EVIDENCE_RESUME_V1',
        'status': 'CLOSED_ENGINEERING_BINARY_EVIDENCE_ONLY',
        'preregistration': prereg,
        'closed_marker_path': 'work_bo/' + marker_path.relative_to(WORK).as_posix(),
        'closed_marker_sha256': sha(marker_path),
        'terminal_review': terminal_review,
        'source_pins': plan['source_pins'],
        'all_evidence_node_hashes_and_types': all_nodes,
        'repository_text_evidence': repo_text,
        'text_and_code_content_embedded': False,
        'final_results_binding': {
            'report_repository_path': 'RADIO_PROGRESS_BO_2026-10-30.md',
            'commit_binding': 'External delivery index/report records the immutable results commit after publication; no circular archive/results-commit binding is invented.'},
        'operations': 'Restore binary members as data only; UNIX symlink/FIFO entries are rejection-fixture metadata. Obtain exact UTF-8 sources/logs/JSON from their repository paths at the stated preregistration or external final results commit. Verify all hashes before any independently authorized later work. Never rerun old or closed BO identities.',
        'remaining_phases': 'Limited paired synthetic controls, full 839-rate paired controls and actual HIP45688 input/search are separate and unactivated.'}
    resume_bytes = (json.dumps(resume, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    resume_row = {'path': 'RESUME_BO.json', 'bytes': len(resume_bytes),
                  'sha256': hashlib.sha256(resume_bytes).hexdigest()}
    manifest = {
        'schema': 'SETI_BO_CLOSED_ENGINEERING_BINARY_ARCHIVE_V1',
        'status': 'CLOSED_ENGINEERING_BINARY_EVIDENCE_TRANSPORT_ONLY',
        'created_utc': created,
        'closed_marker_path': 'work_bo/' + marker_path.relative_to(WORK).as_posix(),
        'closed_marker_sha256': sha(marker_path),
        'terminal_review': terminal_review,
        'plan_sha256': sha(plan_path),
        'source_pins_verified': source_count,
        'preregistration': prereg,
        'all_evidence_nodes_verified': all_nodes,
        'binary_and_typed_node_members': members,
        'repository_text_evidence': repo_text,
        'repository_text_and_code_contents_embedded': False,
        'packaging_script_repository_path': 'build_bo_delivery.py',
        'packaging_script_sha256': packaging_script_sha,
        'resume': resume_row,
        'archive_members': len(members) + 2,
        'archived_binary_and_node_payload_bytes': sum(row['bytes'] for row in members),
        'all_evidence_bytes_verified': sum(row['bytes'] for row in all_nodes),
        'no_failed_or_partial_binary_evidence_discarded': True,
        'all_repository_text_hashes_and_pointers_preserved': True,
        'text_evidence_route': 'Exact UTF-8 source/text/log/JSON contents are stored only in the GitHub repository; this binary archive carries their hashes/pointers only.',
        'astronomical_arrays_opened': 0,
        'RNG_draws': 0,
        'new_scores': 0,
        'new_archive_requests': 0,
        'new_coverage_credit': 0,
        'scope_limit': 'Engineering evidence only; all original historical failures remain unchanged. No synthetic recovery, FAP, sensitivity or astronomical qualification follows from packaging.'
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    write_json_exclusive(start_path, {
        'schema': 'SETI_BO_PACKAGING_START_V1', 'started_utc': created,
        'output_path': str(output), 'input_evidence_node_count': len(all_nodes),
        'selected_binary_and_typed_node_count': len(members),
        'repository_text_evidence_count': len(repo_text),
        'closed_marker_sha256': manifest['closed_marker_sha256'],
        'plan_sha256': manifest['plan_sha256'], 'no_overwrite_no_retry': True})
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as archive:
        for path, row in selected:
            require(identity(path) == signatures[path.relative_to(WORK).as_posix()], 'Evidence identity changed before ZIP write')
            if row['node_type'] == 'regular':
                archive.write(path, row['path'])
            else:
                info = zipfile.ZipInfo(row['path'])
                info.create_system = 3
                info.external_attr = (path.lstat().st_mode & 0xffff) << 16
                if row['node_type'] == 'directory':
                    info.external_attr |= 0x10
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, node_payload(path))
        archive.writestr(resume_row['path'], resume_bytes)
        archive.writestr('MANIFEST_BO.json', manifest_bytes)
    with zipfile.ZipFile(output) as archive:
        require(len(archive.infolist()) == manifest['archive_members'], 'ZIP member count differs')
        names = [info.filename for info in archive.infolist()]
        require(len(names) == len(set(names)), 'Duplicate ZIP member')
        require(archive.testzip() is None, 'ZIP CRC verification failed')
        for row in members + [resume_row]:
            count, digest = member_digest(archive, row['path'])
            require(count == row['bytes'] and digest == row['sha256'], 'ZIP member SHA mismatch: ' + row['path'])
            if row.get('node_type') in {'symlink', 'fifo', 'directory'}:
                archived = archive.getinfo(row['path'])
                require(archived.create_system == 3
                        and (archived.external_attr >> 16) & 0xffff == row['unix_st_mode'] & 0xffff,
                        'ZIP special-node UNIX type/mode changed: ' + row['path'])
        require(archive.read('MANIFEST_BO.json') == manifest_bytes, 'Embedded manifest differs')
    require(inventory() == before_paths, 'Evidence file set changed while packaging')
    for path, row in zip(before_paths, all_nodes, strict=True):
        descriptor = describe_node(path)
        require(identity(path) == signatures[path.relative_to(WORK).as_posix()]
                and descriptor == {key: value for key, value in row.items() if key != 'path'},
                'Original evidence changed during ZIP packaging: ' + str(path))
    require(Path(__file__).read_bytes() == script_bytes, 'Packaging source changed during execution')
    require(verify_source_pins(plan) == source_count, 'Frozen source set changed')
    require(validate_terminal(marker_path) == terminal_review, 'Terminal evidence changed')
    archive_bytes = output.stat().st_size
    archive_sha256 = sha(output)
    parts = []
    if archive_bytes > args.part_bytes:
        with output.open('rb') as stream:
            index = 0
            while True:
                block = stream.read(args.part_bytes)
                if not block:
                    break
                index += 1
                path = output.with_name(output.name + f'.part{index:02d}')
                with path.open('xb') as target:
                    target.write(block)
                parts.append({'path': str(path), 'file_name': path.name, 'bytes': len(block),
                              'sha256': hashlib.sha256(block).hexdigest()})
        total, joined_hash = concatenate_digest([Path(row['path']) for row in parts])
        require(total == archive_bytes and joined_hash == archive_sha256, 'Part concatenation differs from ZIP')
    with manifest_path.open('xb') as stream:
        stream.write(manifest_bytes)
    report = {
        'schema': 'SETI_BO_PACKAGING_VERIFICATION_V1',
        'status': 'PASS_CLOSED_ENGINEERING_ARCHIVE_VERIFIED',
        'completed_utc': datetime.now(timezone.utc).isoformat(),
        'archive_path': str(output), 'archive_bytes': archive_bytes,
        'archive_sha256': archive_sha256, 'archive_members': manifest['archive_members'],
        'manifest_path': str(manifest_path),
        'manifest_bytes': len(manifest_bytes),
        'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
        'all_evidence_nodes_verified': len(all_nodes),
        'archived_binary_and_typed_nodes': len(members),
        'binary_output_files': sum(row['node_type'] == 'regular' for row in members),
        'repository_UTF8_text_files_excluded_with_hashes_and_pointers': len(repo_text),
        'repository_source_text_or_packaging_script_content_embedded': False,
        'directory_nodes_preserved': sum(row['node_type'] == 'directory' for row in members),
        'special_rejection_fixture_nodes_preserved': sum(row['node_type'] in {'symlink', 'fifo'} for row in members),
        'source_pins_verified': source_count,
        'preregistration': prereg,
        'resume_bytes': len(resume_bytes), 'resume_sha256': resume_row['sha256'],
        'actual_terminal_review': terminal_review,
        'archive_CRC_and_all_member_SHA256_verified': True,
        'special_node_UNIX_types_modes_and_payloads_verified': True,
        'all_original_source_and_output_bytes_unchanged': True,
        'binary_only_archive_scope_verified': True,
        'parts': parts,
        'part_concatenation_verified': bool(parts),
        'astronomical_arrays_opened': 0, 'RNG_draws': 0, 'new_scores': 0,
        'no_qualification_beyond_explicit_engineering_gates': True
    }
    write_json_exclusive(report_path, report)
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
