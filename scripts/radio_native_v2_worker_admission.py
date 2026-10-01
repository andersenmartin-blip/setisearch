#!/usr/bin/env python3
"""Read-only checks of supplied preparation-worker evidence; no authority.

This stdlib-only module can be imported by an isolated ``-I -S -B`` child.
It checks an independently retained *exact bundle file* SHA256, the supplied
public-preread structure, fixed worker argv/environment and materialized pins
before a caller writes anything. It does not contact GitHub or establish that
a claimed immutable public readback actually happened. The materialized
fixture's execution guard and all remaining pipeline gates remain required.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

SCHEMA = 'radio-native-v2-worker-admission-bundle-v1'
RECEIPT_SCHEMA = 'radio-native-v2-worker-admission-local-check-v1'
SELF = 'scripts/radio_native_v2_worker_admission.py'
FIXTURE = 'scripts/radio_native_v2_compact_eight_case_resource_fixture.py'
NAMESPACE = 'radio-native-v2-compact-eight-input-control-20261001a'
PREFIX = 'results_radio_native_v2_compact_eight_input_control_20261001a'
PLAN_SCHEMA = 'radio-native-v2-compact-eight-input-resource-control-v1-prospective-plan'
PREREAD_SCHEMA = 'radio-native-v2-compact-eight-input-resource-control-v1-public-preread'
FREEZE_SCHEMA = 'radio-native-v2-runner-broker-runtime-freeze-v1'
FREEZE_NAMESPACE = 'radio-native-v2-engineering-20260930a'
CHILD_ENVIRONMENT = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}
AUTHORITY = {'execution_authorized': False, 'reservation_authorized': False,
    'scientific_execution_authorized': False, 'native_case_reservations': 0,
    'native_case_executions': 0, 'scientific_cases_run': 0, 'rng_draws': 0,
    'telescope_reads': 0, 'actual_functions_sdk_calls': 0, 'actual_connector_calls': 0,
    'network_fetches': 0, 'actual_git_processes': 0, 'real_public_github_mutations': 0,
    'automatic_retry': False, 'native_case_binding_verified': False,
    'host_ledger_join_complete': False, 'hidden_http_bytes_known': False}
FREEZE_DISABLED = ('reservation_authorized', 'rng_authorized', 'execution_authorized',
    'scientific_execution_authorized', 'restart_authorized', 'transport_integration_qualified')
ENVIRONMENT_KEYS = ('PATH', 'PYTHONPATH', 'PYTHONHOME', 'PYTHONSAFEPATH', 'PYTHONNOUSERSITE',
    'NODE_OPTIONS', 'NODE_PATH', 'NODE_ICU_DATA', 'LD_LIBRARY_PATH', 'LD_PRELOAD',
    'OPENSSL_CONF', 'OPENSSL_MODULES', 'SSL_CERT_FILE', 'SSL_CERT_DIR',
    'GIT_EXEC_PATH', 'GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_SYSTEM', 'GIT_CONFIG_GLOBAL',
    'GIT_CONFIG_COUNT', 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_OBJECT_DIRECTORY', 'GIT_NAMESPACE')
BUNDLE_KEYS = frozenset(('schema', 'namespace', 'case_ordinal', 'execution_scope',
    'code_root', 'derived_root', 'plan', 'complete_freeze', 'public_preread',
    'plan_sha256', 'complete_freeze_sha256', 'public_preread_sha256'))
DERIVED_FILES = frozenset(('prepare.py', 'fresh-caller.js', 'lossless-helper.js'))
MAX_JSON_BYTES = 16 * 1024**2
MAX_SOURCE_BYTES = 2 * 1024**2
MIB = 1024**2
ORIGINAL_LIMITS = {'case_calls': 64, 'run_calls': 512,
    'case_request_bytes': 48*MIB, 'run_request_bytes': 384*MIB,
    'case_response_bytes': 64*MIB, 'run_response_bytes': 512*MIB,
    'case_seconds': 600, 'run_seconds': 4800, 'rss_bytes': 512*MIB,
    'case_storage_bytes': 192*MIB, 'run_storage_bytes': 1536*MIB}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _exact(value, expected, label):
    if canonical(value) != canonical(expected):
        raise ValueError('Exact worker preparation evidence differs: ' + label)


def _sha(value, label):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Exact lowercase SHA256 required: ' + label)
    return value


def _ordinal(value):
    if type(value) is not int or not 0 <= value < 8:
        raise ValueError('Exact integer outer case ordinal 0..7 required')
    return value


def _absolute(path):
    value = os.fspath(path)
    if (type(value) is not str or not value.startswith('/') or value == '/'
            or '\\' in value or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value[1:].split('/'))):
        raise ValueError('Canonical absolute worker path required')
    return value


def _relative(value):
    if (type(value) is not str or not value or PurePosixPath(value).is_absolute()
            or '\\' in value or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Canonical relative materialized source path required')
    return value


def _directory(path):
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in _absolute(path)[1:].split('/'):
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_nlink,
            info.st_mtime_ns, info.st_ctime_ns)


def read_pinned_file(path, *, maximum=None, sole_link=True, retain=False):
    """Read one stable inode after walking every ancestor without symlinks."""
    value = _absolute(path); parent, name = value.rsplit('/', 1)
    directory = _directory(parent) if parent else os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    fd = None
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or (sole_link and before.st_nlink != 1)
                or (maximum is not None and before.st_size > maximum)):
            raise ValueError('Bounded sole-link regular worker evidence required: ' + value)
        digest = hashlib.sha256(); count = 0; parts = []
        while True:
            raw = os.read(fd, 65536)
            if not raw: break
            count += len(raw)
            if maximum is not None and count > maximum:
                raise ValueError('Worker evidence bound exceeded: ' + value)
            digest.update(raw)
            if retain: parts.append(raw)
        after = os.fstat(fd)
        named = os.stat(name, dir_fd=directory, follow_symlinks=False)
        again = _directory(parent) if parent else os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        try:
            if (os.fstat(directory).st_dev, os.fstat(directory).st_ino) != (
                    os.fstat(again).st_dev, os.fstat(again).st_ino):
                raise ValueError('Worker evidence ancestor directory replaced')
        finally:
            os.close(again)
        if _identity(before) != _identity(after) or _identity(after) != _identity(named) or count != after.st_size:
            raise ValueError('Worker evidence changed during independent read')
        return {'bytes': count, 'sha256': digest.hexdigest()}, b''.join(parts) if retain else None
    finally:
        if fd is not None: os.close(fd)
        os.close(directory)


def _pin_map(pins, *, absolute=False):
    if type(pins) is not dict or not pins:
        raise ValueError('Nonempty exact worker source pin inventory required')
    for path, pin in pins.items():
        (_absolute if absolute else _relative)(path)
        if (type(pin) is not dict or set(pin) != {'bytes', 'sha256'}
                or type(pin['bytes']) is not int or not 0 < pin['bytes'] <= MAX_SOURCE_BYTES):
            raise ValueError('Exact bounded integer source byte count and SHA pin required')
        _sha(pin['sha256'], path)


def source_domain(ordinal):
    return b'seti-compact-eight-input-sha256-counter-v1\0' + NAMESPACE.encode() + b'\0' + _ordinal(ordinal).to_bytes(8, 'big')


def _validate_plan(plan):
    if type(plan) is not dict or plan.get('schema') != PLAN_SCHEMA or plan.get('namespace') != NAMESPACE:
        raise ValueError('Fixed compact-control prospective plan required')
    if plan.get('mode') != 'PROSPECTIVE_NOT_EXECUTED' or plan.get('execution_status') != 'BLOCKED_PREPARATION_REVIEW':
        raise ValueError('Worker check requires the still-blocked prospective plan')
    for name, value in AUTHORITY.items():
        _exact(plan.get(name), value, 'plan authority ' + name)
    for name in ('large_source_generation_admitted', 'large_inputs_generated', 'activation_guard_complete',
                 'complete_resource_measurement_join_qualified', 'prospective_shared_storage_allocation_complete'):
        if plan.get(name) is not False:
            raise ValueError('Unfinished execution claim refused: ' + name)
    for name in ('complete_runtime_freeze_required', 'public_immutable_preread_required',
                 'lossless_evidence_required', 'retained_raw_inputs_must_not_be_duplicated'):
        if plan.get(name) is not True:
            raise ValueError('Original preparation requirement omitted: ' + name)
    if plan.get('scope_reuse_or_retry_permitted') is not False:
        raise ValueError('Scope reuse/retry cannot be admitted')
    blockers = plan.get('execution_blockers')
    if type(blockers) is not list or len(blockers) != 5 or any(type(row) is not str or not row for row in blockers):
        raise ValueError('All five unresolved original execution blockers required')
    _exact(plan.get('child_environment'), CHILD_ENVIRONMENT, 'plan child environment')
    _exact(plan.get('original_limits'), ORIGINAL_LIMITS, 'original fixed resource limits')
    _pin_map(plan.get('code_files'))
    if not {SELF, FIXTURE}.issubset(plan['code_files']):
        raise ValueError('Worker validator and materialized blocking fixture must both be pinned')
    _pin_map(plan.get('derived_code'))
    if set(plan['derived_code']) != DERIVED_FILES:
        raise ValueError('All three exact prospective derived source pins required')
    cases = plan.get('cases')
    if type(cases) is not list or len(cases) != 8:
        raise ValueError('Exactly eight fixed prospective metadata cases required')
    for ordinal, case in enumerate(cases):
        if type(case) is not dict or type(case.get('ordinal')) is not int or case['ordinal'] != ordinal:
            raise ValueError('Ordered exact outer ordinal case metadata required')
        for name, expected in (('source_case_id', NAMESPACE + f'/case{ordinal:02d}'),
                ('source_domain_hex', source_domain(ordinal).hex()),
                ('archive_prefix', PREFIX + f'/case{ordinal:02d}-fixed')):
            _exact(case.get(name), expected, 'fixed case ' + name)
        for name, expected in (('source_bytes', 26*1024**2), ('archive_files', 28),
                ('archive_bytes', 36875057), ('source_read_fragments', 38),
                ('mock_connector_operations', 6), ('mock_delivery_operations', 6),
                ('real_legacy_tail_operations', 1), ('courier_charged_calls_expected', 56),
                ('case_operation_reservation', 64)):
            if type(case.get(name)) is not int or case[name] != expected:
                raise ValueError('Original exact engineering case allocation differs: ' + name)
    runtime = plan.get('runtime_executables')
    if type(runtime) is not dict or set(runtime) != {'python', 'node'}:
        raise ValueError('Exact Python and Node prospective executable pins required')
    for name, record in runtime.items():
        if type(record) is not dict or set(record) != {'path', 'bytes', 'sha256'}:
            raise ValueError('Exact prospective runtime executable record required')
        _absolute(record['path']); _sha(record['sha256'], name)
        if type(record['bytes']) is not int or record['bytes'] <= 0:
            raise ValueError('Exact positive executable byte count required')
    supplement = plan.get('engineering_runtime_supplement')
    expected_supplement_keys = {'schema', 'files', 'repository_bytecode_copied',
        'child_python_flags', 'child_repository_imports_use_fresh_source_only', 'scientific_runtime_qualified'}
    if type(supplement) is not dict or set(supplement) != expected_supplement_keys:
        raise ValueError('Exact prospective engineering runtime supplement structure required')
    for key, value in (('schema', 'radio-native-v2-compact-eight-input-resource-control-v1-engineering-runtime-supplement'),
            ('repository_bytecode_copied', False), ('child_python_flags', ['-I', '-S', '-B']),
            ('child_repository_imports_use_fresh_source_only', True), ('scientific_runtime_qualified', False)):
        _exact(supplement[key], value, 'supplement ' + key)
    if type(supplement['files']) is not dict:
        raise ValueError('Exact supplement file pin map required')
    for path, record in supplement['files'].items():
        _absolute(path)
        if type(record) is not dict or set(record) != {'bytes', 'sha256'} or type(record['bytes']) is not int or record['bytes'] < 0:
            raise ValueError('Exact nonnegative supplement byte count and SHA pin required')
        _sha(record['sha256'], path)


def _validate_freeze(freeze):
    """Strict original local schema checks, without claiming expected closure."""
    fields = {'schema', 'freeze_kind', 'mode', 'namespace', *FREEZE_DISABLED,
        'transport_qualification', 'repository_code_inventory', 'code_sha256s',
        'input_file_inventory', 'input_sha256s', 'runtime_file_inventory', 'runtime_sha256s',
        'executables', 'git_exec_path', 'git_runtime_file_inventory', 'git_node_elf_inventory',
        'unavailable_unused_python_extensions', 'python', 'numpy', 'environment_fingerprints', 'coverage'}
    if (type(freeze) is not dict or set(freeze) != fields or freeze['schema'] != FREEZE_SCHEMA
            or freeze['freeze_kind'] != 'COMPLETE_RUNNER_BROKER_RUNTIME'
            or freeze['mode'] != 'PROSPECTIVE_ENGINEERING_ONLY' or freeze['namespace'] != FREEZE_NAMESPACE):
        raise ValueError('Exact complete original runner freeze structure required')
    if any(freeze[name] is not False for name in FREEZE_DISABLED) or freeze['transport_qualification'] is not None:
        raise ValueError('Supplied runner freeze cannot grant authority')
    for inventory, hashes in (('repository_code_inventory', 'code_sha256s'),
                              ('input_file_inventory', 'input_sha256s'),
                              ('runtime_file_inventory', 'runtime_sha256s')):
        if type(freeze[inventory]) is not list or type(freeze[hashes]) is not dict or freeze[inventory] != sorted(freeze[hashes]):
            raise ValueError('Exact original freeze map/list join required: ' + inventory)
        for path, digest in freeze[hashes].items():
            (_absolute if hashes == 'runtime_sha256s' else _relative)(path)
            _sha(digest, path)
    if not {'scripts/radio_native_v2_runner_freeze.py', 'scripts/radio_native_v2_broker_host.js'}.issubset(freeze['code_sha256s']):
        raise ValueError('Original freeze helper and broker host must be pinned')
    for path in set(freeze['code_sha256s']) & set(freeze['input_sha256s']):
        _exact(freeze['code_sha256s'][path], freeze['input_sha256s'][path], 'overlapping freeze file pin')
    executables = freeze['executables']
    if type(executables) is not dict or set(executables) != {'python', 'git', 'node'}:
        raise ValueError('Original Python/Git/Node executable identities required')
    for name, record in executables.items():
        if type(record) is not dict or set(record) != {'invocation', 'resolved', 'sha256', 'version'}:
            raise ValueError('Original exact executable record required')
        _absolute(record['invocation']); _absolute(record['resolved']); _sha(record['sha256'], name)
        if freeze['runtime_sha256s'].get(record['resolved']) != record['sha256']:
            raise ValueError('Original executable/runtime hash differs')
        if ((name == 'node' and type(record['version']) is not dict)
                or (name != 'node' and type(record['version']) is not str)):
            raise ValueError('Original measured executable version type differs')
    _absolute(freeze['git_exec_path'])
    for key in ('git_runtime_file_inventory', 'git_node_elf_inventory'):
        if type(freeze[key]) is not list or freeze[key] != sorted(set(freeze[key])) or not set(freeze[key]).issubset(freeze['runtime_sha256s']):
            raise ValueError('Original Git/Node runtime subinventory differs')
    unavailable = freeze['unavailable_unused_python_extensions']
    if (type(unavailable) is not dict or not set(unavailable).issubset(freeze['runtime_sha256s'])
            or any(type(lines) is not list or not lines
                   or any(type(line) is not str or 'not found' not in line for line in lines)
                   for lines in unavailable.values())):
        raise ValueError('Original unavailable Python extension inventory differs')
    if any(type(freeze[key]) is not str or not freeze[key] for key in ('python', 'numpy')):
        raise ValueError('Original measured Python/NumPy versions required')
    fingerprints = freeze['environment_fingerprints']
    if type(fingerprints) is not dict or set(fingerprints) != set(ENVIRONMENT_KEYS):
        raise ValueError('Exact original parent environment fingerprint inventory required')
    for key, value in fingerprints.items():
        if value is not None: _sha(value, key)
    coverage = freeze['coverage']
    if type(coverage) is not dict:
        raise ValueError('Original local runtime coverage limitations required')
    for key in ('external_tool_transport_runtime_frozen', 'operating_system_kernel_frozen',
                'git_credential_and_network_configuration_frozen', 'git_script_interpreters_qualified',
                'arbitrary_node_modules_qualified', 'python_cached_bytecode_execution_qualified',
                'python_import_source_policy_qualified'):
        if coverage.get(key) is not False:
            raise ValueError('Unsupported complete runtime coverage claim refused: ' + key)


def _validate_bundle(bundle, *, ordinal):
    _ordinal(ordinal)
    if type(bundle) is not dict or set(bundle) != BUNDLE_KEYS or bundle['schema'] != SCHEMA:
        raise ValueError('Exact worker admission bundle required')
    if bundle['namespace'] != NAMESPACE or type(bundle['case_ordinal']) is not int or bundle['case_ordinal'] != ordinal:
        raise ValueError('Bundle namespace/outer ordinal differs from expected worker')
    scope = _absolute(bundle['execution_scope']); case_root = scope + f'/cases/case{ordinal:02d}'
    _exact(bundle['code_root'], case_root + '/frozen-code', 'fixed materialized code root')
    _exact(bundle['derived_root'], case_root + '/derived', 'fixed materialized derived root')
    plan = bundle['plan']; freeze = bundle['complete_freeze']; proof = bundle['public_preread']
    _validate_plan(plan); _validate_freeze(freeze)
    for key, value in (('plan_sha256', plan), ('complete_freeze_sha256', freeze), ('public_preread_sha256', proof)):
        _sha(bundle[key], key)
        _exact(bundle[key], hashlib.sha256(canonical(value)).hexdigest(), 'canonical embedded ' + key)
    expected = {'schema': PREREAD_SCHEMA, 'namespace': NAMESPACE,
        'plan_sha256': bundle['plan_sha256'], 'complete_freeze_sha256': bundle['complete_freeze_sha256'],
        'public_immutable_readback_verified': True, 'engineering_control_admitted': True,
        'code_files_verified': plan['code_files'], **AUTHORITY}
    if type(proof) is not dict or set(proof) != {*expected, 'preparation_commit'}:
        raise ValueError('Exact supplied immutable public-preread proof structure required')
    for key, value in expected.items():
        _exact(proof[key], value, 'supplied preread ' + key)
    if type(proof['preparation_commit']) is not str or not re.fullmatch('[0-9a-f]{40}', proof['preparation_commit']):
        raise ValueError('Full immutable public preparation commit ID required')
    for path, wanted in plan['code_files'].items():
        hashes = freeze['input_sha256s'] if path.startswith('tests/') else freeze['code_sha256s']
        if hashes.get(path) != wanted['sha256']:
            raise ValueError('Complete original freeze omitted prospective material/test source pin: ' + path)
    for name, wanted in plan['runtime_executables'].items():
        if freeze['executables'][name]['resolved'] != wanted['path'] or freeze['runtime_sha256s'].get(wanted['path']) != wanted['sha256']:
            raise ValueError('Original freeze does not bind prospective executable: ' + name)
    return case_root


def build_admission_bundle(plan, complete_freeze, public_preread, *, execution_scope, ordinal):
    """Return metadata only; caller retains canonical(bundle)+newline bytes."""
    scope = _absolute(execution_scope); ordinal = _ordinal(ordinal)
    case_root = scope + f'/cases/case{ordinal:02d}'
    bundle = {'schema': SCHEMA, 'namespace': NAMESPACE, 'case_ordinal': ordinal,
        'execution_scope': scope, 'code_root': case_root + '/frozen-code', 'derived_root': case_root + '/derived',
        'plan': plan, 'complete_freeze': complete_freeze, 'public_preread': public_preread,
        'plan_sha256': hashlib.sha256(canonical(plan)).hexdigest(),
        'complete_freeze_sha256': hashlib.sha256(canonical(complete_freeze)).hexdigest(),
        'public_preread_sha256': hashlib.sha256(canonical(public_preread)).hexdigest()}
    _validate_bundle(bundle, ordinal=ordinal)
    return json.loads(canonical(bundle))


def bundle_bytes(bundle):
    """Exactly these retained bytes, including newline, are the argv digest."""
    if type(bundle) is not dict: raise ValueError('Worker bundle object required')
    _validate_bundle(bundle, ordinal=bundle.get('case_ordinal'))
    return canonical(bundle) + b'\n'


def expected_worker_argv(bundle, bundle_path, *, ordinal, expected_bundle_sha256, role='prepare'):
    if role != 'prepare':
        raise ValueError('Only the fixed preparation worker role is described')
    case_root = _validate_bundle(bundle, ordinal=ordinal)
    digest = _sha(expected_bundle_sha256, 'independently retained exact bundle bytes')
    path = _absolute(bundle_path)
    _exact(path, case_root + '/worker-admission.json', 'fixed case admission bundle path')
    python = bundle['plan']['runtime_executables']['python']['path']
    case = bundle['plan']['cases'][ordinal]
    return [python, '-I', '-S', '-B', case_root + '/derived/prepare.py',
            case_root, python, NAMESPACE, str(ordinal), case['archive_prefix'], path, digest]


def _tree_inventory(root):
    """Walk descriptor-relative material trees; reject aliases and extra bytes."""
    root = _absolute(root); directory = _directory(root); found = set(); directories = set()
    def walk(fd, prefix):
        before = os.fstat(fd)
        for name in sorted(os.listdir(fd)):
            if name in ('', '.', '..') or '/' in name or '\\' in name or re.search(r'[\x00-\x1f\x7f]', name):
                raise ValueError('Canonical materialized entry name required')
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            relative = prefix + name
            if stat.S_ISDIR(info.st_mode):
                directories.add(_relative(relative))
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    opened = os.fstat(child)
                    if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                        raise ValueError('Materialized directory changed during inventory')
                    walk(child, relative + '/')
                finally: os.close(child)
            elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                found.add(_relative(relative))
            else:
                raise ValueError('Materialized tree alias or special file refused')
        after = os.fstat(fd)
        if _identity(before) != _identity(after):
            raise ValueError('Materialized directory changed during inventory')
    try: walk(directory, '')
    finally: os.close(directory)
    return found, directories


def _expected_directories(files):
    return {str(parent) for path in files for parent in PurePosixPath(path).parents if str(parent) != '.'}


def load_bundle(bundle_path, *, expected_bundle_sha256):
    expected = _sha(expected_bundle_sha256, 'independently retained exact bundle bytes')
    actual, raw = read_pinned_file(bundle_path, maximum=MAX_JSON_BYTES, retain=True)
    if actual['sha256'] != expected:
        raise ValueError('Exact admission bundle bytes changed from independently retained digest')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value: raise ValueError('Duplicate admission JSON property refused')
            value[key] = item
        return value
    def nonfinite(value):
        raise ValueError('Nonfinite admission JSON refused')
    bundle = json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)
    if raw != canonical(bundle) + b'\n':
        raise ValueError('Exact canonical admission bundle plus newline required')
    return bundle


def validate_worker_admission(bundle_path, *, role='prepare', ordinal, argv, environment,
        expected_bundle_sha256):
    """Validate retained local claims only; never launch, mutate, or authorize."""
    if type(argv) is not list or any(type(item) is not str for item in argv):
        raise ValueError('Exact complete worker argv string list required')
    if type(environment) is not dict:
        raise ValueError('Exact complete child environment dictionary required')
    _exact(environment, CHILD_ENVIRONMENT, 'complete minimal child environment')
    bundle = load_bundle(_absolute(bundle_path), expected_bundle_sha256=expected_bundle_sha256)
    expected = expected_worker_argv(bundle, bundle_path, ordinal=ordinal,
        expected_bundle_sha256=expected_bundle_sha256, role=role)
    _exact(argv, expected, 'exact preparation worker argv')
    plan = bundle['plan']; code_root = bundle['code_root']; derived_root = bundle['derived_root']
    case_root = bundle['execution_scope'] + f'/cases/case{ordinal:02d}'
    case_directory = _directory(case_root)
    try:
        previous_outputs = {'preparation-identity.json', 'deterministic-source.bin', 'prepared.json',
                            'caller-result.json', 'caller-summary.json', 'store'} & set(os.listdir(case_directory))
        if previous_outputs:
            raise ValueError('Existing preparation output/scope reuse refused: ' + ','.join(sorted(previous_outputs)))
    finally: os.close(case_directory)
    for root, pins, label in ((code_root, plan['code_files'], 'code'),
                             (derived_root, plan['derived_code'], 'derived')):
        files, directories = _tree_inventory(root)
        _exact(sorted(files), sorted(pins), 'exact materialized ' + label + ' inventory')
        _exact(sorted(directories), sorted(_expected_directories(pins)), 'exact materialized ' + label + ' directory inventory')
    for prefix, pins in ((code_root, plan['code_files']), (derived_root, plan['derived_code'])):
        for path, wanted in pins.items():
            actual, _ = read_pinned_file(prefix + '/' + path, maximum=MAX_SOURCE_BYTES)
            _exact(actual, wanted, 'materialized source ' + path)
    loaded_self, _ = read_pinned_file(str(Path(__file__).absolute()), maximum=MAX_SOURCE_BYTES)
    _exact(loaded_self, plan['code_files'][SELF], 'loaded worker validator source')
    executable = plan['runtime_executables']['python']
    if str(Path(executable['path']).resolve()) != executable['path']:
        raise ValueError('Prospective Python executable path alias refused')
    _exact(str(Path(sys.executable).resolve()), executable['path'], 'actual child Python executable')
    actual, _ = read_pinned_file(executable['path'], sole_link=False)
    _exact(actual, {'bytes': executable['bytes'], 'sha256': executable['sha256']}, 'actual isolated Python executable bytes')
    # Reopen exact bundle after all material reads; a valid initial snapshot
    # must not silently become a different admission file during the checks.
    load_bundle(bundle_path, expected_bundle_sha256=expected_bundle_sha256)
    return {'schema': RECEIPT_SCHEMA, 'status': 'LOCAL_SUPPLIED_PREREAD_VALIDATED_EXECUTION_BLOCKED',
        'namespace': NAMESPACE, 'case_ordinal': ordinal,
        'source_case_id': plan['cases'][ordinal]['source_case_id'],
        'source_domain_hex': source_domain(ordinal).hex(),
        'archive_prefix': plan['cases'][ordinal]['archive_prefix'], 'role': role,
        'bundle_path': str(bundle_path), 'bundle_exact_file_sha256': expected_bundle_sha256,
        'plan_canonical_sha256': bundle['plan_sha256'],
        'complete_freeze_canonical_sha256': bundle['complete_freeze_sha256'],
        'public_preread_canonical_sha256': bundle['public_preread_sha256'],
        'preparation_commit_claim': bundle['public_preread']['preparation_commit'],
        'supplied_public_preread_structure_checked': True,
        'publication_claim_independently_verified': False,
        'remote_immutable_publication_fetched': False,
        'independently_retained_bundle_digest_matched': True,
        'exact_worker_argv_checked': True, 'complete_child_environment_checked': True,
        'current_materialized_code_and_derived_pins_checked': True,
        'fresh_preparation_output_names_absent': True,
        'loaded_validator_code': loaded_self,
        'complete_expected_runtime_closure_verified': False,
        'current_parent_environment_verified': False,
        'runtime_and_supplement_join_verified': False,
        'fixture_execution_guard_still_required': True,
        'pipeline_integration_qualified': False, 'large_source_generation_admitted': False,
        'all_original_execution_blockers_closed': False,
        'checks_remain_subject_to_postcheck_mutation': True, **AUTHORITY}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true', required=True)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--bundle-sha256', required=True)
    parser.add_argument('--ordinal', type=int, required=True)
    args = parser.parse_args()
    path = _absolute(args.bundle)
    bundle = load_bundle(path, expected_bundle_sha256=args.bundle_sha256)
    argv = expected_worker_argv(bundle, path, ordinal=args.ordinal,
        expected_bundle_sha256=args.bundle_sha256)
    result = validate_worker_admission(path, ordinal=args.ordinal, argv=argv,
        environment=dict(os.environ), expected_bundle_sha256=args.bundle_sha256)
    print(canonical(result).decode())


if __name__ == '__main__':
    main()
