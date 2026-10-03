#!/usr/bin/env python3
"""Construct exact P preread or proposed A marker bytes; never activates state.

The trusted outer operator independently fetches immutable D/P records and
supplies their commit/tree/blob pins plus the externally pinned source proof.
Only local metadata is read. Output is canonical JSON plus one newline to
stdout. Save it in scratch for review; this helper has no output-path option,
no Git/network commands, and no marker/journal/claim/scope creation.

Common CLI pins (all required): --root ABS, --plan REL --plan-sha256 RAW_SHA,
--complete-freeze REL --complete-freeze-sha256 RAW_SHA, --source-proof ABS
--source-proof-sha256 RAW_SHA, --preparation-commit D --preparation-tree D_TREE,
--plan-blob D_PLAN_BLOB --complete-freeze-blob D_FREEZE_BLOB.

Use --kind preread to produce the sole P preread document. After the outer
operator independently publishes/reads P, use --kind marker and additionally
--preread REL --preread-sha256 RAW_SHA --preread-commit P --preread-tree P_TREE
--preread-blob P_PREREAD_BLOB --control-scope ABS_E_SCOPE. The outer P readback
must independently establish that plan/freeze blobs remain the supplied D blob
IDs. These parameters attest immutable public bytes only; the helper does not
verify current runtime custody, publish A, consume spending, or launch control.

The exact output schemas are PREREAD_SCHEMA or ACTIVATION_SCHEMA below.
Canonical document SHA256 excludes the output newline; raw/file SHA256 and
Git blob SHA1 include it. No output wrapper or extra authority fields are added.
"""
import argparse
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import stat
import sys

METADATA_LIMIT = 128 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
FREEZE_SCHEMA = 'radio-native-v2-runner-broker-runtime-freeze-v1'
AUTHORITY_FIELDS = ('reservation_authorized', 'rng_authorized', 'execution_authorized',
    'scientific_execution_authorized', 'restart_authorized', 'transport_integration_qualified')
PREREAD_SCHEMA = 'radio-native-v2-compact-eight-input-resource-control-v1-public-preread'
PLAN_SCHEMA = 'radio-native-v2-compact-eight-input-resource-control-v1-prospective-plan'
CONTROL_NAMESPACE = 'radio-native-v3-compact-eight-input-control-20261003e'
ACTIVATION_SCHEMA = 'radio-native-v2-control-single-activation-v2'
ACTIVATION_NAMESPACE = 'radio-native-v3-control-activation-transition-20261003e'
MARKER_PATH = 'config/radio_native_v3_control_activation_20261003e.activate.json'
CONTROL_SCOPE_NAME = 'results_radio_native_v3_compact_eight_input_control_20261003e'
LEDGER_NAME = '.radio-native-v3-invocation-ledger-20261003e'
DISABLED = ('reservation_authorized', 'rng_authorized', 'scientific_execution_authorized',
    'native_execution_authorized', 'restart_authorized', 'automatic_retry')
AUTHORITY = {'execution_authorized': False, 'reservation_authorized': False,
    'scientific_execution_authorized': False, 'native_case_reservations': 0,
    'native_case_executions': 0, 'scientific_cases_run': 0, 'rng_draws': 0,
    'telescope_reads': 0, 'actual_functions_sdk_calls': 0, 'actual_connector_calls': 0,
    'network_fetches': 0, 'actual_git_processes': 0, 'real_public_github_mutations': 0,
    'automatic_retry': False, 'native_case_binding_verified': False,
    'host_ledger_join_complete': False, 'hidden_http_bytes_known': False}


def _hash(value, length, label):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{%d}' % length, value) is None:
        raise ValueError('Exact lowercase hash required: ' + label)
    return value


def _relative(value):
    if (not isinstance(value, str) or not value or '\\' in value
            or re.search(r'[\x00-\x1f\x7f]', value)
            or PurePosixPath(value).is_absolute()
            or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Canonical repository-relative path required')
    try:
        value.encode('utf-8', 'strict')
    except UnicodeError as error:
        raise ValueError('UTF-8 path required') from error
    return value


def _absolute(value):
    value = os.fspath(value)
    if (not isinstance(value, str) or not value.startswith('/') or value == '/'
            or '\\' in value or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value[1:].split('/'))):
        raise ValueError('Strict canonical absolute path required')
    return value


def _directory_signature(observed):
    if not stat.S_ISDIR(observed.st_mode):
        raise ValueError('Real directory required')
    return observed.st_dev, observed.st_ino, observed.st_mode


def _file_signature(observed):
    if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
        raise ValueError('Sole-link regular file required')
    return (observed.st_dev, observed.st_ino, observed.st_mode, observed.st_nlink,
            observed.st_size, observed.st_mtime_ns, observed.st_ctime_ns)


def _open_directory(absolute, witnesses):
    """Walk from / with directory descriptors; no ancestor symlink follows."""
    _absolute(absolute)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open('/', flags)
    current = ''
    try:
        for component in absolute[1:].split('/'):
            following = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
            current += '/' + component
            observed = _directory_signature(os.fstat(descriptor))
            if current in witnesses and witnesses[current] != observed:
                raise ValueError('Directory identity changed: ' + current)
            witnesses.setdefault(current, observed)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_regular(absolute, directories):
    _absolute(absolute)
    parent, name = absolute.rsplit('/', 1)
    # All callers use non-root parents, including their metadata files.
    descriptor = _open_directory(parent, directories)
    try:
        return os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                       dir_fd=descriptor)
    finally:
        os.close(descriptor)


def _stat_file(absolute, directories):
    descriptor = _open_regular(absolute, directories)
    try:
        return _file_signature(os.fstat(descriptor))
    finally:
        os.close(descriptor)


def _read_file(absolute, directories, expected_signature=None, *, metadata=False):
    descriptor = _open_regular(absolute, directories)
    try:
        before = _file_signature(os.fstat(descriptor))
        if expected_signature is not None and before != expected_signature:
            raise ValueError('File changed before read: ' + absolute)
        size = before[4]
        if metadata and size > METADATA_LIMIT:
            raise ValueError('Metadata file exceeds bounded read limit')
        sha256 = hashlib.sha256()
        git_blob = hashlib.sha1(('blob %d\0' % size).encode('ascii'))
        chunks = [] if metadata else None
        count = 0
        while True:
            block = os.read(descriptor, CHUNK_SIZE)
            if not block:
                break
            count += len(block)
            if count > size:
                raise ValueError('File grew while being read: ' + absolute)
            sha256.update(block)
            git_blob.update(block)
            if metadata:
                chunks.append(block)
        after = _file_signature(os.fstat(descriptor))
        if after != before or count != size:
            raise ValueError('File changed during read: ' + absolute)
        # Also bind the lexical pathname after closing races with renamed files.
        if _stat_file(absolute, directories) != before:
            raise ValueError('Path identity changed during read: ' + absolute)
        return {'sha256': sha256.hexdigest(), 'git_blob_sha': git_blob.hexdigest(),
                'bytes': count, 'signature': before,
                'raw': b''.join(chunks) if metadata else None}
    finally:
        os.close(descriptor)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON object key: ' + key)
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError('Nonfinite JSON constant refused: ' + value)


def _metadata(absolute, expected_sha256, directories):
    _hash(expected_sha256, 64, 'metadata SHA256')
    pin = _read_file(_absolute(absolute), directories, metadata=True)
    if pin['sha256'] != expected_sha256:
        raise ValueError('Raw metadata SHA256 differs: ' + absolute)
    try:
        value = json.loads(pin.pop('raw').decode('utf-8', 'strict'),
                           object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('Strict UTF-8 JSON metadata required') from error
    if not isinstance(value, dict):
        raise ValueError('JSON metadata object required')
    return value, pin


def _count(value, label):
    if type(value) is not int or value < 0:
        raise ValueError('Nonnegative integer count required: ' + label)
    return value


def _freeze_selection(freeze, expected_code_count, expected_input_count, expected_unique_count):
    if (freeze.get('schema') != FREEZE_SCHEMA
            or freeze.get('freeze_kind') != 'COMPLETE_RUNNER_BROKER_RUNTIME'
            or freeze.get('mode') != 'PROSPECTIVE_ENGINEERING_ONLY'):
        raise ValueError('Complete prospective engineering freeze required')
    if any(freeze.get(field) is not False for field in AUTHORITY_FIELDS):
        raise ValueError('Freeze cannot confer execution or transport authority')
    if freeze.get('transport_qualification') is not None:
        raise ValueError('Freeze transport qualification must remain absent')
    maps = []
    for inventory_name, hashes_name, expected_count in (
            ('repository_code_inventory', 'code_sha256s', expected_code_count),
            ('input_file_inventory', 'input_sha256s', expected_input_count)):
        inventory, hashes = freeze.get(inventory_name), freeze.get(hashes_name)
        if (not isinstance(inventory, list) or not isinstance(hashes, dict)
                or any(not isinstance(path, str) for path in inventory)
                or inventory != sorted(hashes)):
            raise ValueError('Exact sorted inventory/hash-map join required: ' + inventory_name)
        if len(inventory) != _count(expected_count, inventory_name):
            raise ValueError('Independently pinned inventory count differs: ' + inventory_name)
        for path, sha256 in hashes.items():
            _relative(path)
            _hash(sha256, 64, path)
        maps.append(hashes)
    code, inputs = maps
    shared = set(code) & set(inputs)
    if any(code[path] != inputs[path] for path in shared):
        raise ValueError('Overlapping code/input identities conflict')
    selected = {**code, **inputs}
    if len(selected) != _count(expected_unique_count, 'unique paths'):
        raise ValueError('Independently pinned unique joined count differs')
    if not selected:
        raise ValueError('Nonempty frozen source selection required')
    return code, inputs, selected


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _equal(value, expected, label):
    # JSON booleans and integers are distinct protocol values.
    if canonical(value) != canonical(expected):
        raise ValueError('Exact protocol value required: ' + label)


def _bound_local_metadata(root, relative, sha256, expected_blob, directories):
    relative = _relative(relative)
    _hash(expected_blob, 40, 'independently read public blob')
    value, pin = _metadata(root + '/' + relative, sha256, directories)
    if pin['git_blob_sha'] != expected_blob:
        raise ValueError('Local metadata bytes differ from independently read public blob: ' + relative)
    return value, pin


def _plan(root, plan):
    if (plan.get('schema') != PLAN_SCHEMA or plan.get('namespace') != CONTROL_NAMESPACE
            or plan.get('invocation_repository_root') != root
            or plan.get('invocation_ledger_root') != root + '/' + LEDGER_NAME):
        raise ValueError('Exact current e engineering plan/root/ledger binding required')
    for key, expected in AUTHORITY.items():
        _equal(plan.get(key), expected, 'plan ' + key)
    if not isinstance(plan.get('code_files'), dict) or not plan['code_files']:
        raise ValueError('Nonempty exact plan code-file pin inventory required')
    for path, record in plan['code_files'].items():
        _relative(path)
        if not isinstance(record, dict) or set(record) != {'bytes', 'sha256'}:
            raise ValueError('Exact plan source pin structure required')
        _count(record['bytes'], path)
        _hash(record['sha256'], 64, path)


def _proof(root, proof, plan, freeze, freeze_raw_sha256, preparation_commit, preparation_tree):
    for key, expected in (
            ('schema', 'radio-native-v3-public-source-content-address-proof-v1'),
            ('status', 'PASS_SELECTED_FROZEN_BYTE_EQUIVALENCE'),
            ('repository_root', root), ('immutable_commit', preparation_commit),
            ('immutable_tree', preparation_tree), ('freeze_sha256', freeze_raw_sha256),
            ('recursive_tree_truncated', False), ('all_selected_frozen_paths_equal', True),
            ('all_public_blobs_individually_http_downloaded', False),
            ('scientific_execution_authorized', False), ('execution_authorized', False),
            ('reservation_authorized', False), ('transport_integration_qualified', False)):
        _equal(proof.get(key), expected, 'source proof ' + key)
    code, inputs, selected = _freeze_selection(freeze, proof.get('code_path_count'),
        proof.get('input_path_count'), proof.get('selected_unique_path_count'))
    rows = proof.get('files')
    if not isinstance(rows, list) or len(rows) != len(selected):
        raise ValueError('Complete exact source proof rows required')
    checked = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Source proof file object required')
        path = _relative(row.get('path'))
        if path in checked or path not in selected:
            raise ValueError('Duplicate/unselected source proof path')
        _equal(row.get('sha256'), selected[path], 'source proof selected SHA256')
        _hash(row.get('git_blob_sha'), 40, 'source proof public blob')
        _count(row.get('bytes'), 'source proof selected bytes')
        if row.get('public_git_mode') not in ('100644', '100755'):
            raise ValueError('Regular public source proof Git mode required')
        for key, expected in (('freeze_sha256_equal', True), ('public_blob_sha_equal', True),
                ('public_blob_size_equal', True), ('code_selected', path in code),
                ('input_selected', path in inputs)):
            _equal(row.get(key), expected, 'source proof ' + key)
        checked[path] = {'bytes': row['bytes'], 'sha256': row['sha256']}
    if set(checked) != set(selected):
        raise ValueError('Source proof/freeze inventory join differs')
    for path, pin in plan['code_files'].items():
        if checked.get(path) != pin:
            raise ValueError('Plan code-file pin absent/different in public source proof: ' + path)


def expected_preread(plan, freeze, preparation_commit):
    return {'schema': PREREAD_SCHEMA, 'namespace': CONTROL_NAMESPACE,
            'plan_sha256': hashlib.sha256(canonical(plan)).hexdigest(),
            'complete_freeze_sha256': hashlib.sha256(canonical(freeze)).hexdigest(),
            'public_immutable_readback_verified': True, 'engineering_control_admitted': True,
            'code_files_verified': plan['code_files'], 'preparation_commit': preparation_commit,
            **AUTHORITY}


def build(*, kind, root, plan, plan_sha256, complete_freeze, complete_freeze_sha256,
          source_proof, source_proof_sha256, preparation_commit, preparation_tree,
          plan_blob, complete_freeze_blob, preread=None, preread_sha256=None,
          preread_commit=None, preread_tree=None, preread_blob=None, control_scope=None):
    root = _absolute(root)
    _hash(preparation_commit, 40, 'independently read preparation D commit')
    _hash(preparation_tree, 40, 'independently read preparation D tree')
    directories = {}
    plan_value, plan_pin = _bound_local_metadata(root, plan, plan_sha256, plan_blob, directories)
    freeze_value, freeze_pin = _bound_local_metadata(root, complete_freeze,
        complete_freeze_sha256, complete_freeze_blob, directories)
    proof_value, proof_pin = _metadata(_absolute(source_proof), source_proof_sha256, directories)
    _plan(root, plan_value)
    _proof(root, proof_value, plan_value, freeze_value, complete_freeze_sha256,
        preparation_commit, preparation_tree)
    proposed_preread = expected_preread(plan_value, freeze_value, preparation_commit)
    optional = (preread, preread_sha256, preread_commit, preread_tree, preread_blob, control_scope)
    metadata = [(root + '/' + plan, plan_pin), (root + '/' + complete_freeze, freeze_pin),
                (source_proof, proof_pin)]
    if kind == 'preread':
        if any(value is not None for value in optional):
            raise ValueError('Marker parameters are forbidden while constructing preread P')
        result = proposed_preread
    elif kind == 'marker':
        if any(value is None for value in optional):
            raise ValueError('Complete independently read P preread pins/scope required for proposed A marker')
        _hash(preread_commit, 40, 'independently read P commit')
        _hash(preread_tree, 40, 'independently read P tree')
        if preread_commit == preparation_commit:
            raise ValueError('P preread must have a distinct immutable commit from D preparation')
        preread_value, preread_pin = _bound_local_metadata(root, preread, preread_sha256,
            preread_blob, directories)
        _equal(preread_value, proposed_preread, 'exact P public preread structure and original D binding')
        if _absolute(control_scope) != root + '/' + CONTROL_SCOPE_NAME:
            raise ValueError('Exact new e control scope required')
        if len({plan, complete_freeze, preread, MARKER_PATH}) != 4:
            raise ValueError('Plan/freeze/preread/marker repository paths must be distinct')
        result = {'schema': ACTIVATION_SCHEMA, 'namespace': ACTIVATION_NAMESPACE,
            'activate': True, 'preread_commit': preread_commit, 'preread_tree': preread_tree,
            'plan_sha256': proposed_preread['plan_sha256'],
            'complete_freeze_sha256': proposed_preread['complete_freeze_sha256'],
            'execution_preread_sha256': hashlib.sha256(canonical(preread_value)).hexdigest(),
            'independent_preread_readback': {'verified': True, 'commit': preread_commit,
                'tree': preread_tree, 'blobs': {'plan': plan_blob, 'complete_freeze': complete_freeze_blob,
                    'execution_preread': preread_blob}},
            'one_control_invocation': True, 'control_scope': control_scope,
            **{key: False for key in DISABLED}}
        metadata.append((root + '/' + preread, preread_pin))
    else:
        raise ValueError('Explicit preread or marker construction kind required')
    for path, pin in metadata:
        if _stat_file(path, directories) != pin['signature']:
            raise ValueError('Pinned admission metadata changed while constructing document')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('preread', 'marker'), required=True)
    for key in ('root', 'plan', 'plan-sha256', 'complete-freeze', 'complete-freeze-sha256',
            'source-proof', 'source-proof-sha256', 'preparation-commit', 'preparation-tree',
            'plan-blob', 'complete-freeze-blob'):
        parser.add_argument('--' + key, required=True)
    for key in ('preread', 'preread-sha256', 'preread-commit', 'preread-tree', 'preread-blob', 'control-scope'):
        parser.add_argument('--' + key)
    try:
        value = build(**vars(parser.parse_args(argv)))
    except (ValueError, OSError) as error:
        parser.exit(2, 'public admission document construction refused: ' + str(error) + '\n')
    # These bytes are an operator draft, not installed activation state.
    sys.stdout.buffer.write(canonical(value) + b'\n')
    return 0


if __name__ == '__main__':
    main()
