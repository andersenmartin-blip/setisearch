#!/usr/bin/env python3
"""Exact secret-free activation parent environment contract; no execution.

The ordinary automation environment contains unrelated proxy, credential and
session variables. It is not a prospective execution environment. This module
derives a minimal public environment from pinned runtime executable paths and
refuses extras before any protected worker could be admitted.
"""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path, PurePosixPath
import re
import stat
import sys

SCHEMA = 'radio-native-v2-activation-parent-environment-v1'
PLAN_SCHEMA = 'radio-native-v2-compact-eight-input-resource-control-v1-prospective-plan'
FREEZE_SCHEMA = 'radio-native-v2-runner-broker-runtime-freeze-v1'
MAX_JSON_BYTES = 8 * 1024 * 1024
AUTHORITY = {'execution_authorized': False, 'reservation_authorized': False,
    'scientific_execution_authorized': False, 'native_case_reservations': 0,
    'native_case_executions': 0, 'scientific_cases_run': 0, 'rng_draws': 0,
    'telescope_reads': 0, 'network_fetches': 0, 'actual_connector_calls': 0,
    'actual_functions_sdk_calls': 0, 'automatic_retry': False}
PLATFORM_SCHEMA = 'radio-native-v2-bounded-activation-platform-v1'
STATUS_FIELDS = ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb',
    'NoNewPrivs', 'Seccomp', 'Seccomp_filters')
KERNEL_PATHS = {
    'boot_id': '/proc/sys/kernel/random/boot_id',
    'io_uring_disabled': '/proc/sys/kernel/io_uring_disabled',
    'osrelease': '/proc/sys/kernel/osrelease',
    'ostype': '/proc/sys/kernel/ostype',
    'ptrace_scope': '/proc/sys/kernel/yama/ptrace_scope',
    'unprivileged_userns_clone': '/proc/sys/kernel/unprivileged_userns_clone',
    'version': '/proc/sys/kernel/version',
    'max_user_namespaces': '/proc/sys/user/max_user_namespaces'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _bounded_public_text(path, maximum=4096):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise ValueError('Bounded regular public platform field required: '+str(path))
        raw = os.read(fd, maximum+1); after = os.fstat(fd)
        if len(raw) > maximum or _identity(before) != _identity(after):
            raise ValueError('Public platform field changed during read: '+str(path))
    finally: os.close(fd)
    return raw.rstrip(b'\n').decode('utf-8', 'strict')


def platform_contract():
    """Secret-free bounded activation identity; not a claim to hash the kernel."""
    status = {}
    for line in _bounded_public_text('/proc/self/status', maximum=65536).splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            if key in STATUS_FIELDS: status[key] = value.strip()
    if set(status) != set(STATUS_FIELDS):
        raise ValueError('Complete bounded process security status required')
    if any(not re.fullmatch('[0-9a-f]{16}', status[key]) for key in STATUS_FIELDS[:5]):
        raise ValueError('Exact capability masks required')
    if any(not re.fullmatch('[0-9]+', status[key]) for key in STATUS_FIELDS[5:]):
        raise ValueError('Exact numeric process security fields required')
    kernel = {}
    for name, value in KERNEL_PATHS.items():
        path = Path(value)
        kernel[name] = _bounded_public_text(path) if path.exists() else None
    if not re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', kernel['boot_id'] or ''):
        raise ValueError('Exact lowercase kernel boot identity required')
    uname = os.uname()
    return {'schema': PLATFORM_SCHEMA,
        'uname': {'sysname': uname.sysname, 'nodename': uname.nodename,
            'release': uname.release, 'version': uname.version, 'machine': uname.machine},
        'kernel_public_fields': kernel, 'process_security': status,
        'page_size': os.sysconf('SC_PAGE_SIZE'), 'clock_ticks': os.sysconf('SC_CLK_TCK'),
        'byteorder': sys.byteorder, 'filesystem_encoding': sys.getfilesystemencoding(),
        'python_implementation': sys.implementation.name,
        'python_cache_tag': sys.implementation.cache_tag,
        'python_version': platform.python_version(), 'libc': list(platform.libc_ver()),
        'lsm_current_hex': Path('/proc/self/attr/current').read_bytes()[:4096].hex(),
        'secret_bearing_values_included': False,
        'operating_system_kernel_bytes_frozen': False,
        'activation_time_exact_recheck_required': True}


def validate_platform(expected):
    if type(expected) is not dict or expected.get('schema') != PLATFORM_SCHEMA:
        raise ValueError('Exact bounded activation platform contract required')
    actual = platform_contract()
    if actual != expected:
        changed = sorted(key for key in set(actual) | set(expected)
            if canonical(actual.get(key)) != canonical(expected.get(key)))
        raise ValueError('Activation platform differs; changed='+','.join(changed))
    return actual


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_nlink,
        info.st_mtime_ns, info.st_ctime_ns)


def read_json(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or str(path) != str(path.absolute()):
        raise ValueError('Canonical absolute contract path required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_JSON_BYTES:
            raise ValueError('Bounded sole-link contract JSON required')
        raw = bytearray()
        while len(raw) <= MAX_JSON_BYTES:
            block = os.read(fd, min(65536, MAX_JSON_BYTES + 1 - len(raw)))
            if not block: break
            raw.extend(block)
        after = os.fstat(fd)
        if len(raw) != before.st_size or _identity(before) != _identity(after) or _identity(path.lstat()) != _identity(after):
            raise ValueError('Contract JSON changed during read')
    finally:
        os.close(fd)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('Duplicate contract JSON property refused')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError('Nonfinite contract JSON refused')))
    if type(value) is not dict: raise ValueError('Contract JSON object required')
    return value, {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _absolute_executable(record, label):
    if type(record) is not dict or type(record.get('path', record.get('resolved'))) is not str:
        raise ValueError('Pinned runtime executable required: '+label)
    value = record.get('path', record.get('resolved'))
    path = PurePosixPath(value)
    if not path.is_absolute() or any(part in ('', '.', '..') for part in path.parts[1:]):
        raise ValueError('Canonical absolute runtime executable required: '+label)
    if type(record.get('sha256')) is not str or not re.fullmatch('[a-f0-9]{64}', record['sha256']):
        raise ValueError('Pinned runtime SHA256 required: '+label)
    return value


def expected_environment(plan, freeze):
    if plan.get('schema') != PLAN_SCHEMA or plan.get('execution_status') != 'BLOCKED_PREPARATION_REVIEW':
        raise ValueError('Exact blocked prospective plan required')
    if freeze.get('schema') != FREEZE_SCHEMA or freeze.get('mode') != 'PROSPECTIVE_ENGINEERING_ONLY':
        raise ValueError('Exact prospective runtime freeze required')
    if any(plan.get(key) is not False for key in ('execution_authorized', 'reservation_authorized',
            'scientific_execution_authorized')):
        raise ValueError('Environment contract cannot derive from an authorized plan')
    if plan.get('activation_platform_contract', {}).get('schema') != PLATFORM_SCHEMA:
        raise ValueError('Bounded activation platform contract missing from plan')
    python = _absolute_executable(plan.get('runtime_executables', {}).get('python'), 'plan python')
    node = _absolute_executable(plan.get('runtime_executables', {}).get('node'), 'plan node')
    frozen = freeze.get('executables', {})
    frozen_python = _absolute_executable(frozen.get('python'), 'freeze python')
    frozen_node = _absolute_executable(frozen.get('node'), 'freeze node')
    git = _absolute_executable(frozen.get('git'), 'freeze git')
    if Path(python).resolve() != Path(frozen_python).resolve() or Path(node).resolve() != Path(frozen_node).resolve():
        raise ValueError('Plan and complete freeze runtime executable paths differ')
    paths = []
    for value in (python, node, git, '/usr/bin/x', '/bin/x'):
        parent = str(PurePosixPath(value).parent)
        if parent not in paths: paths.append(parent)
    return {'PATH': ':'.join(paths), 'LANG': 'C', 'LC_ALL': 'C',
        'HOME': '/nonexistent', 'PYTHONSAFEPATH': '1', 'PYTHONNOUSERSITE': '1',
        'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
        'GIT_TERMINAL_PROMPT': '0', 'GIT_NO_LAZY_FETCH': '1'}


def validate(plan, freeze, actual):
    expected = expected_environment(plan, freeze)
    if type(actual) is not dict or any(type(k) is not str or type(v) is not str for k, v in actual.items()):
        raise ValueError('Exact string parent environment required')
    if actual != expected:
        missing = sorted(set(expected)-set(actual)); extra = sorted(set(actual)-set(expected))
        changed = sorted(key for key in set(actual)&set(expected) if actual[key] != expected[key])
        raise ValueError('Activation parent environment differs; missing='+','.join(missing)+
            '; extra='+','.join(extra)+'; changed='+','.join(changed))
    observed_platform = validate_platform(plan['activation_platform_contract'])
    return {'schema': SCHEMA, 'status': 'EXACT_ACTIVATION_PARENT_ENVIRONMENT_VERIFIED',
        'environment': expected,
        'environment_sha256': hashlib.sha256(canonical(expected)).hexdigest(),
        'complete_parent_environment_frozen': True,
        'secret_bearing_ambient_environment_inherited': False,
        'runtime_paths_derived_from_pinned_plan_and_freeze': True,
        'bounded_activation_platform': observed_platform,
        'bounded_activation_platform_contract_verified': True,
        'operating_system_kernel_bytes_frozen': False,
        'activation_time_recheck_required': True,
        'complete_runtime_closure_qualified': False,
        'public_immutable_execution_preread_verified': False,
        'activation_guard_complete': False, **AUTHORITY}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true', required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--complete-freeze', type=Path, required=True)
    args = parser.parse_args()
    plan, plan_pin = read_json(args.plan.absolute())
    freeze, freeze_pin = read_json(args.complete_freeze.absolute())
    result = validate(plan, freeze, dict(os.environ))
    result.update({'plan_pin': plan_pin, 'complete_freeze_pin': freeze_pin,
        'observed_argv': list(sys.orig_argv),
        'isolated_no_site_no_bytecode': bool(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode)})
    if not result['isolated_no_site_no_bytecode']:
        raise RuntimeError('Exact isolated no-site no-bytecode parent checker required')
    print(canonical(result).decode())


if __name__ == '__main__':
    main()
