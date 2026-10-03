#!/usr/bin/env python3
"""Verify a public failed-control closure without claiming live storage custody."""
import hashlib
import json
import re
from datetime import datetime
from pathlib import PurePosixPath


SCHEMA = 'radio-native-v2-archival-control-closure-v1'
LABELS = ('spend_record', 'launch_start', 'launch_terminal',
    'terminal_scope_inventory', 'source_preservation')
MAX_FILE_BYTES = 1024 * 1024
MAX_STORAGE_BYTES = 1536 * 1024 * 1024
SHA256 = re.compile(r'[a-f0-9]{64}')
COMMIT = re.compile(r'[a-f0-9]{40}')
CONTROL_NAME = 'results_radio_native_v2_compact_control_20261002c'
LEDGER_NAME = '.radio-native-v2-invocation-ledger-20261002c'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode('utf-8') + b'\n'


def _integer(value, *, minimum=0, maximum=MAX_STORAGE_BYTES):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError('Bounded exact archival integer required')
    return value


def _path(value, *, absolute):
    if (type(value) is not str or not value
            or any(ord(character) < 32 for character in value)
            or value.startswith('/') is not absolute
            or value.startswith('//')
            or '..' in value.split('/')
            or str(PurePosixPath(value)) != value
            or value in ('.', '/')):
        raise ValueError('Canonical archived path required')
    return PurePosixPath(value)


def _digest(value, pattern):
    if type(value) is not str or not pattern.fullmatch(value):
        raise ValueError('Exact archival digest required')


def _utc(value):
    if type(value) is not str:
        raise ValueError('Canonical archival UTC timestamp required')
    try:
        parsed = datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError as error:
        raise ValueError('Canonical archival UTC timestamp required') from error
    if parsed.strftime('%Y-%m-%dT%H:%M:%SZ') != value:
        raise ValueError('Canonical archival UTC timestamp required')
    return parsed


def _inventory_rows(inventory, scope):
    """Check archive metadata internally; do not open its labelled live paths."""
    directories = inventory['directories']; files = inventory['files']
    if (type(directories) is not list or len(directories) != 21
            or type(files) is not list or len(files) != 68):
        raise ValueError('Exact archived file and directory rows required')
    root = scope.name
    directory_paths = set(); file_paths = set()
    logical = allocated = frozen = 0
    for row in directories:
        if type(row) is not dict or set(row) != {'path', 'mode', 'allocated_bytes'}:
            raise ValueError('Exact archived directory row required')
        path = str(_path(row['path'], absolute=False))
        if (path != root and not path.startswith(root + '/')) or path in directory_paths:
            raise ValueError('Unique archived directory within control scope required')
        if (row['mode'] not in ('0o700', '0o755')
                or (path == root or path == root + '/cases'
                    or path.startswith(root + '/cases/')) and row['mode'] != '0o700'):
            raise ValueError('Valid archived directory mode and private cases required')
        directory_paths.add(path)
        allocated += _integer(row['allocated_bytes'])
    for row in files:
        if type(row) is not dict or set(row) != {
                'path', 'bytes', 'allocated_bytes', 'links', 'sha256', 'git_blob_sha'}:
            raise ValueError('Exact archived file row required')
        path = str(_path(row['path'], absolute=False))
        if (not path.startswith(root + '/') or path in file_paths
                or path in directory_paths):
            raise ValueError('Unique archived file within control scope required')
        if _integer(row['links'], minimum=1) != 1:
            raise ValueError('Unaliased archived file required')
        _digest(row['sha256'], SHA256); _digest(row['git_blob_sha'], COMMIT)
        file_paths.add(path)
        logical += _integer(row['bytes'])
        allocated += _integer(row['allocated_bytes'])
        frozen += path.startswith(root + '/frozen-code/')
    if (root not in directory_paths
            or any(str(PurePosixPath(path).parent) not in directory_paths
                for path in (directory_paths | file_paths) - {root})):
        raise ValueError('Complete archived directory ancestry required')
    cases = root + '/cases'
    expected_cases = {cases + '/case%02d' % number for number in range(8)}
    if (cases not in directory_paths
            or {path for path in directory_paths | file_paths
                if path.startswith(cases + '/')} != expected_cases
            or not expected_cases <= directory_paths):
        raise ValueError('Exactly eight empty archived case directories required')
    if (logical != inventory['logical_bytes'] or allocated != inventory['allocated_bytes']
            or frozen != inventory['frozen_materialized_files']):
        raise ValueError('Archived inventory rows differ from declared totals')


def _launch_details(start, scope):
    _digest(start['config_sha256'], SHA256)
    for field in ('public_preread_commit', 'public_sidecar_commit'):
        _digest(start[field], COMMIT)
    if _path(start['private_c_ledger'], absolute=True) != scope.parent / LEDGER_NAME:
        raise ValueError('Archived private ledger label differs from control generation')
    argv = start['argv']
    if (type(argv) is not list or len(argv) != 8
            or any(type(argument) is not str for argument in argv)):
        raise ValueError('Exact archived isolated launcher argv required')
    interpreter = _path(argv[0], absolute=True)
    if (not re.fullmatch(r'python3(?:\.[0-9]+)?', interpreter.name)
            or argv[1:] != ['-I', '-S', '-B',
                str(scope.parent / 'scripts/radio_native_v2_compact_control_launch.py'),
                '--run', '--config-sha256', start['config_sha256']]):
        raise ValueError('Exact archived isolated launcher argv required')
    environment = start['environment']
    fixed = {'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1',
        'GIT_NO_LAZY_FETCH': '1', 'GIT_TERMINAL_PROMPT': '0', 'HOME': '/nonexistent',
        'LANG': 'C', 'LC_ALL': 'C', 'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1'}
    if (type(environment) is not dict or set(environment) != set(fixed) | {'PATH'}
            or any(environment[key] != value for key, value in fixed.items())
            or type(environment['PATH']) is not str):
        raise ValueError('Exact archived isolated launcher environment required')
    search_paths = environment['PATH'].split(':')
    if (not search_paths or search_paths[0] != str(interpreter.parent)
            or len(set(search_paths)) != len(search_paths)):
        raise ValueError('Canonical archived launcher search path required')
    for path in search_paths:
        _path(path, absolute=True)
    return _utc(start['utc_start'])


def _raw(raw, pin):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_FILE_BYTES:
        raise ValueError('Bounded archival closure bytes required')
    if (type(pin) is not dict or set(pin) != {'bytes', 'sha256'}
            or type(pin['bytes']) is not int or pin['bytes'] != len(raw)
            or type(pin['sha256']) is not str or not SHA256.fullmatch(pin['sha256'])
            or hashlib.sha256(raw).hexdigest() != pin['sha256']):
        raise ValueError('Archival closure differs from exact independent pin')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value: raise ValueError('Duplicate archival JSON property refused')
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=unique)
    if type(value) is not dict or canonical(value) != raw:
        raise ValueError('Canonical newline-terminated archival JSON required')
    return value


def verify_archival_closure(files, *, expected_pins):
    """Return a non-authorizing closure receipt for the exact five-file bundle."""
    if (type(files) is not dict or set(files) != set(LABELS)
            or type(expected_pins) is not dict or set(expected_pins) != set(LABELS)):
        raise ValueError('Exact five-file archival closure bundle required')
    values = {label: _raw(files[label], expected_pins[label]) for label in LABELS}
    spend = values['spend_record']; start = values['launch_start']
    terminal = values['launch_terminal']; inventory = values['terminal_scope_inventory']
    preservation = values['source_preservation']

    if (set(spend) != {'schema', 'activation_commit', 'activation_identity_sha256',
            'activation_receipt_sha256', 'control_scope', 'one_invocation_spent', 'state'}
            or spend['schema'] != 'radio-native-v2-control-invocation-spend-v1'
            or spend['one_invocation_spent'] is not True
            or spend['state'] != 'SPENT_BEFORE_WORKLOAD'):
        raise ValueError('Exact permanently spent public record required')
    for field in ('activation_identity_sha256', 'activation_receipt_sha256'):
        if type(spend[field]) is not str or not SHA256.fullmatch(spend[field]):
            raise ValueError('Exact spend identity SHA256 required')
    if type(spend['activation_commit']) is not str or not COMMIT.fullmatch(spend['activation_commit']):
        raise ValueError('Exact activation commit required')
    scope = spend['control_scope']
    scope_path = _path(scope, absolute=True)
    if scope_path.name != CONTROL_NAME:
        raise ValueError('Exact archived c control generation required')

    required_start = {'schema', 'scope', 'activation_commit', 'status',
        'automatic_retry', 'restart_authorized', 'journal_created_empty_before_launcher',
        'control_scope_absent_before_launch', 'native_execution_authorized',
        'scientific_execution_authorized', 'private_c_ledger', 'argv', 'environment',
        'config_sha256', 'public_preread_commit', 'public_sidecar_commit', 'utc_start'}
    if (set(start) != required_start
            or start['schema'] != 'radio-native-v2-c-single-launch-start-v1'
            or start['scope'] != scope or start['activation_commit'] != spend['activation_commit']
            or start['status'] != 'ONE_EXACT_ENGINEERING_LAUNCH_NO_AUTOMATIC_RETRY'
            or start['automatic_retry'] is not False or start['restart_authorized'] is not False
            or start['journal_created_empty_before_launcher'] is not True
            or start['control_scope_absent_before_launch'] is not True
            or start['native_execution_authorized'] is not False
            or start['scientific_execution_authorized'] is not False):
        raise ValueError('Exact closed launch-start contract required')
    started = _launch_details(start, scope_path)

    terminal_expected = {'schema', 'status', 'launcher_exit_code',
        'protected_launcher_attempts', 'completed_engineering_cases',
        'scope_case_directories', 'durable_claim_records', 'private_c_claim_filename',
        'private_c_claim_bytes', 'private_c_claim_sha256', 'permanently_spent',
        'automatic_retry', 'restart_authorized', 'native_execution_authorized',
        'scientific_execution_authorized', 'telescope_reads', 'rng_draws', 'terminal_utc'}
    spend_pin = expected_pins['spend_record']['sha256']
    if (set(terminal) != terminal_expected
            or terminal['schema'] != 'radio-native-v2-c-single-launch-terminal-v1'
            or terminal['status'] != 'CLOSED_FAILED' or terminal['launcher_exit_code'] != 1
            or terminal['protected_launcher_attempts'] != 1
            or terminal['completed_engineering_cases'] != 0
            or terminal['scope_case_directories'] != 8
            or terminal['durable_claim_records'] != 1
            or terminal['private_c_claim_bytes'] != expected_pins['spend_record']['bytes']
            or terminal['private_c_claim_sha256'] != spend_pin
            or terminal['permanently_spent'] is not True
            or terminal['automatic_retry'] is not False
            or terminal['restart_authorized'] is not False
            or terminal['native_execution_authorized'] is not False
            or terminal['scientific_execution_authorized'] is not False
            or terminal['telescope_reads'] != 0 or terminal['rng_draws'] != 0):
        raise ValueError('Exact closed failed terminal record required')
    for field in ('launcher_exit_code', 'protected_launcher_attempts',
            'completed_engineering_cases', 'scope_case_directories',
            'durable_claim_records', 'private_c_claim_bytes', 'telescope_reads', 'rng_draws'):
        _integer(terminal[field])
    if terminal['private_c_claim_filename'] != 'spent-' + spend['activation_identity_sha256'] + '.json':
        raise ValueError('Spend record filename differs from activation identity')
    if _utc(terminal['terminal_utc']) < started:
        raise ValueError('Archived terminal timestamp precedes launch')

    inventory_expected = {'schema', 'status', 'file_count', 'directory_count',
        'logical_bytes', 'allocated_bytes', 'frozen_materialized_files',
        'all_frozen_files_match_original_sources', 'directories', 'files',
        'all_eight_case_directories_empty', 'completed_engineering_cases',
        'private_c_ledger_not_part_of_scope_inventory', 'scientific_execution_authorized'}
    if (set(inventory) != inventory_expected
            or inventory['schema'] != 'radio-native-v2-c-terminal-scope-inventory-v1'
            or inventory['status'] != 'CLOSED_FAILED'
            or inventory['file_count'] != 68 or inventory['directory_count'] != 21
            or inventory['frozen_materialized_files'] != 49
            or inventory['all_frozen_files_match_original_sources'] is not True
            or inventory['all_eight_case_directories_empty'] is not True
            or inventory['completed_engineering_cases'] != 0
            or inventory['private_c_ledger_not_part_of_scope_inventory'] is not True
            or inventory['scientific_execution_authorized'] is not False):
        raise ValueError('Exact closed failed terminal inventory required')
    for field in ('file_count', 'directory_count', 'frozen_materialized_files',
            'completed_engineering_cases', 'logical_bytes', 'allocated_bytes'):
        _integer(inventory[field])
    if inventory['allocated_bytes'] < inventory['logical_bytes']:
        raise ValueError('Bounded terminal inventory totals required')
    _inventory_rows(inventory, scope_path)

    preservation_expected = {'schema', 'status', 'baseline', 'pin_count',
        'all_pins_match', 'production_source_edits', 'tests_rerun_for_metadata_only',
        'c_frozen_materialized_files_verified_separately',
        'protected_control_invocations_this_turn',
        'prior_541_tests_remain_preparation_evidence_not_actual_c_success',
        'scope_reuse_or_retry_permitted'}
    if (set(preservation) != preservation_expected
            or preservation['schema'] != 'radio-native-v2-c-post-terminal-source-preservation-v1'
            or preservation['status'] != 'ALL_PRIOR_1002_SOURCE_TEST_AND_WRAPPER_PINS_UNCHANGED'
            or preservation['baseline'] != 'results_radio_native_v2_control_integration_20261002a/final-suite-attempt-2-summary.json'
            or preservation['pin_count'] != 1002
            or preservation['all_pins_match'] is not True
            or preservation['production_source_edits'] != 0
            or preservation['tests_rerun_for_metadata_only'] is not False
            or preservation['c_frozen_materialized_files_verified_separately'] != 49
            or preservation['protected_control_invocations_this_turn'] != 1
            or preservation['prior_541_tests_remain_preparation_evidence_not_actual_c_success'] is not True
            or preservation['scope_reuse_or_retry_permitted'] is not False):
        raise ValueError('Exact post-terminal preservation record required')
    for field in ('pin_count', 'production_source_edits',
            'c_frozen_materialized_files_verified_separately',
            'protected_control_invocations_this_turn'):
        _integer(preservation[field])

    return {'schema': SCHEMA, 'activation_commit': spend['activation_commit'],
        'control_scope_label': scope, 'status': 'CLOSED_FAILED',
        'completed_engineering_cases': 0, 'protected_launcher_attempts': 1,
        'permanently_spent': True, 'public_archive_pins_verified': True,
        'archive_evidence_complete': True, 'original_private_journal_observed': False,
        'original_live_scope_observed': False, 'live_storage_continuity_proved': False,
        'storage_join_eligible': False, 'activation_authorized': False,
        'retry_authorized': False, 'scientific_execution_authorized': False,
        'telescope_read_authorized': False,
        'terminal_scope_logical_bytes_label': inventory['logical_bytes'],
        'terminal_scope_allocated_bytes_label': inventory['allocated_bytes']}
