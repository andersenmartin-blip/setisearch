#!/usr/bin/env python3
"""Verify a public failed-control closure without claiming live storage custody."""
import hashlib
import json
import re


SCHEMA = 'radio-native-v2-archival-control-closure-v1'
LABELS = ('spend_record', 'launch_start', 'launch_terminal',
    'terminal_scope_inventory', 'source_preservation')
MAX_FILE_BYTES = 1024 * 1024
SHA256 = re.compile(r'[a-f0-9]{64}')
COMMIT = re.compile(r'[a-f0-9]{40}')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode('utf-8') + b'\n'


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
    if type(scope) is not str or not scope.startswith('/') or scope == '/':
        raise ValueError('Absolute archived control scope required')

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
    if terminal['private_c_claim_filename'] != 'spent-' + spend['activation_identity_sha256'] + '.json':
        raise ValueError('Spend record filename differs from activation identity')

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
    if (type(inventory['logical_bytes']) is not int or inventory['logical_bytes'] < 0
            or type(inventory['allocated_bytes']) is not int
            or inventory['allocated_bytes'] < inventory['logical_bytes']):
        raise ValueError('Bounded terminal inventory totals required')

    preservation_expected = {'schema', 'status', 'baseline', 'pin_count',
        'all_pins_match', 'production_source_edits', 'tests_rerun_for_metadata_only',
        'c_frozen_materialized_files_verified_separately',
        'protected_control_invocations_this_turn',
        'prior_541_tests_remain_preparation_evidence_not_actual_c_success',
        'scope_reuse_or_retry_permitted'}
    if (set(preservation) != preservation_expected
            or preservation['schema'] != 'radio-native-v2-c-post-terminal-source-preservation-v1'
            or preservation['all_pins_match'] is not True
            or preservation['production_source_edits'] != 0
            or preservation['c_frozen_materialized_files_verified_separately'] != 49
            or preservation['protected_control_invocations_this_turn'] != 1
            or preservation['prior_541_tests_remain_preparation_evidence_not_actual_c_success'] is not True
            or preservation['scope_reuse_or_retry_permitted'] is not False):
        raise ValueError('Exact post-terminal preservation record required')

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
