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
import base64
import codecs
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import sys
import types

SCHEMA = 'radio-native-v2-worker-admission-bundle-v3'
ROLE_SCHEMA = 'radio-native-v2-worker-role-admission-bundle-v4'
RECEIPT_SCHEMA = 'radio-native-v2-worker-admission-local-check-v1'
SELF = 'scripts/radio_native_v2_worker_admission.py'
FIXTURE = 'scripts/radio_native_v2_compact_eight_case_resource_fixture.py'
NAMESPACE = 'radio-native-v2-compact-eight-input-control-20261001a'
PREFIX = 'results_radio_native_v2_compact_eight_input_control_20261001a'
PLAN_SCHEMA = 'radio-native-v2-compact-eight-input-resource-control-v1-prospective-plan'
PREREAD_SCHEMA = 'radio-native-v2-compact-eight-input-resource-control-v1-public-preread'
FREEZE_SCHEMA = 'radio-native-v2-runner-broker-runtime-freeze-v1'
FREEZE_NAMESPACE = 'radio-native-v2-engineering-20260930a'
ACTIVATION_RECEIPT_SCHEMA = 'radio-native-v2-control-single-activation-receipt-v2'
ACTIVATION_NAMESPACE = 'radio-native-v2-control-activation-transition-20261002b'
ACTIVATION_MARKER = 'config/radio_native_v2_control_activation_20261002b.activate.json'
SPENT_ACTIVATION_MARKER = 'config/radio_native_v2_control_activation_20261002a.activate.json'
SPENT_ACTIVATION_COMMIT = 'ba1b6c918931a02a84cd23e0e14057bd9f700e40'
CUSTODY_SOURCE = 'scripts/radio_native_v2_runtime_custody.py'
CUSTODY_IMPLEMENTATION_PIN = {'bytes':22519,
    'sha256':'d0cd311c1615a2c299b101ca75b98ba2412b41bb1cfd668725461e4d307fb0b5'}
SPENDING_SOURCE = 'scripts/radio_native_v2_invocation_spending.py'
SPENDING_IMPLEMENTATION_PIN = {'bytes': 15048, 'sha256': 'd659918161562e4b237385872efdc59d0d070feeec47e01b9e0d8ccdbcf05ae0'}
ACTIVATION_DISABLED = ('reservation_authorized', 'rng_authorized',
    'scientific_execution_authorized', 'native_execution_authorized',
    'restart_authorized', 'automatic_retry')
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
    'activation_receipt', 'plan_sha256', 'complete_freeze_sha256',
    'public_preread_sha256', 'activation_receipt_sha256',
    'invocation_spending', 'invocation_spending_sha256'))
DERIVED_FILES = frozenset(('prepare.py', 'fresh-caller.js', 'lossless-helper.js'))
MAX_JSON_BYTES = 16 * 1024**2
MAX_SOURCE_BYTES = 2 * 1024**2
CASE_ROLES = frozenset(('caller', 'command', 'lossless-project', 'lossless-verify-retained'))
WHOLE_ROLES = frozenset(('control', 'verifier'))
ROLES = CASE_ROLES | WHOLE_ROLES | {'prepare'}
SOURCE_READER = 'import os,sys; f=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW); n=int(sys.argv[3]); b=os.pread(f,n,int(sys.argv[2])); assert len(b)==n; sys.stdout.buffer.write(b); os.close(f)'
TAIL_BOOTSTRAP = ('import os,sys,hashlib; p=sys.argv[1]; f=os.open(p,os.O_RDONLY|os.O_NOFOLLOW); '
    's=os.read(f,65537); os.close(f); assert len(s)<=65536 and hashlib.sha256(s).hexdigest()==sys.argv[2], '
    '"Pinned caller-tail helper source differs"; sys.argv=[p]+sys.argv[3:]; '
    'exec(compile(s,p,"exec"),{"__name__":"__main__","__file__":p})')
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


def read_pinned_file(path, *, maximum=None, sole_link=True, retain=False, retain_prefix=0):
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
            elif retain_prefix and count-len(raw) < retain_prefix:
                parts.append(raw[:retain_prefix-(count-len(raw))])
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
        return {'bytes': count, 'sha256': digest.hexdigest()}, b''.join(parts) if retain or retain_prefix else None
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


def _custody_module():
    path = Path(__file__).absolute().parents[1]/CUSTODY_SOURCE
    actual,raw = read_pinned_file(str(path),maximum=MAX_SOURCE_BYTES,retain=True)
    if actual != CUSTODY_IMPLEMENTATION_PIN:
        raise ValueError('Custody source differs from independent worker implementation pin')
    module = types.ModuleType('pinned_worker_runtime_custody'); module.__file__ = str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module


def _spending_module():
    path = Path(__file__).absolute().parents[1]/SPENDING_SOURCE
    actual,raw = read_pinned_file(str(path),maximum=MAX_SOURCE_BYTES,retain=True)
    if actual != SPENDING_IMPLEMENTATION_PIN:
        raise ValueError('Spending source differs from independent worker implementation pin')
    module = types.ModuleType('pinned_worker_invocation_spending'); module.__file__ = str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module


def _custody_contract(freeze, custody):
    manifest = freeze.get('runtime_custody_manifest')
    digest = _sha(freeze.get('runtime_custody_manifest_sha256'),'runtime custody manifest')
    if hashlib.sha256(canonical(manifest)).hexdigest() != digest:
        raise ValueError('Frozen runtime custody manifest canonical hash differs')
    material = {freeze['executables'][name]['resolved'] for name in ('python','node')}
    material.update(path for path in freeze['runtime_file_inventory'] if re.search(r'\.so(?:\.|$)',Path(path).name))
    activation = sorted({freeze['executables']['git']['resolved'],*freeze['git_runtime_file_inventory']} - material)
    custody.validate_manifest_structure(manifest,runtime_paths=freeze['runtime_file_inventory'],
        runtime_sha256s=freeze['runtime_sha256s'],activation_only_paths=activation,
        alias_roots=sorted({str(Path(freeze['executables']['git']['resolved']).parent),freeze['git_exec_path']}))
    return manifest,digest


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
    ledger = _absolute(plan.get('invocation_ledger_root'))
    if Path(ledger).name != '.radio-native-v2-invocation-ledger':
        raise ValueError('Fixed original-repository invocation ledger name required')
    if plan['code_files'].get(SPENDING_SOURCE) != SPENDING_IMPLEMENTATION_PIN:
        raise ValueError('Prospective spending source differs from independent implementation pin')
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
        'unavailable_unused_python_extensions', 'python', 'numpy', 'environment_fingerprints', 'coverage',
        'runtime_custody_manifest','runtime_custody_manifest_sha256'}
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
    if freeze['code_sha256s'].get(CUSTODY_SOURCE) != CUSTODY_IMPLEMENTATION_PIN['sha256']:
        raise ValueError('Frozen custody source must bind the independently reviewed implementation')
    _custody_contract(freeze,_custody_module())


def _validate_activation_receipt(receipt, plan, freeze, proof, *, execution_scope):
    """Recheck the exact outer public-marker receipt before worker writes."""
    expected = {'schema','namespace','activation_commit','activation_tree',
        'activation_parent','activation_public_readback_verified','marker_path',
        'marker_blob','marker_sha256','plan_sha256','complete_freeze_sha256',
        'execution_preread_sha256','one_control_invocation','control_scope',
        'runtime_custody_manifest_sha256','activation_only_runtime_complete',*ACTIVATION_DISABLED}
    if type(receipt) is dict and (receipt.get('marker_path') == SPENT_ACTIVATION_MARKER
            or receipt.get('activation_commit') == SPENT_ACTIVATION_COMMIT):
        raise ValueError('Historical failed activation marker/commit is permanently spent')
    if type(receipt) is not dict or set(receipt) != expected:
        raise ValueError('Exact activation receipt structure required')
    if (receipt['schema'] != ACTIVATION_RECEIPT_SCHEMA
            or receipt['namespace'] != ACTIVATION_NAMESPACE
            or receipt['marker_path'] != ACTIVATION_MARKER
            or receipt['activation_public_readback_verified'] is not True
            or receipt['one_control_invocation'] is not True):
        raise ValueError('Exact one-control public activation receipt required')
    if _absolute(receipt['control_scope']) != _absolute(execution_scope):
        raise ValueError('Activation receipt control scope differs from exact worker execution scope')
    if receipt['activation_only_runtime_complete'] is not True:
        raise ValueError('Activation-only Git use must cease before worker admission')
    if _sha(receipt['runtime_custody_manifest_sha256'],'runtime custody receipt') != freeze['runtime_custody_manifest_sha256']:
        raise ValueError('Activation receipt runtime custody hash differs')
    for key in ('activation_commit','activation_tree','activation_parent','marker_blob'):
        if type(receipt[key]) is not str or not re.fullmatch('[0-9a-f]{40}',receipt[key]):
            raise ValueError('Exact lowercase Git identity required: '+key)
    for key in ('marker_sha256','plan_sha256','complete_freeze_sha256','execution_preread_sha256'):
        _sha(receipt[key],key)
    if receipt['plan_sha256'] != hashlib.sha256(canonical(plan)).hexdigest():
        raise ValueError('Activation receipt plan pin differs')
    if receipt['complete_freeze_sha256'] != hashlib.sha256(canonical(freeze)).hexdigest():
        raise ValueError('Activation receipt freeze pin differs')
    if receipt['execution_preread_sha256'] != hashlib.sha256(canonical(proof)).hexdigest():
        raise ValueError('Activation receipt preread pin differs')
    for key in ACTIVATION_DISABLED:
        if receipt[key] is not False:
            raise ValueError('Activation receipt grants forbidden authority: '+key)


def _validate_prepare_bundle(bundle, *, ordinal):
    _ordinal(ordinal)
    if type(bundle) is not dict or set(bundle) != BUNDLE_KEYS or bundle['schema'] != SCHEMA:
        raise ValueError('Exact worker admission bundle required')
    if bundle['namespace'] != NAMESPACE or type(bundle['case_ordinal']) is not int or bundle['case_ordinal'] != ordinal:
        raise ValueError('Bundle namespace/outer ordinal differs from expected worker')
    scope = _absolute(bundle['execution_scope']); case_root = scope + f'/cases/case{ordinal:02d}'
    _exact(bundle['code_root'], case_root + '/frozen-code', 'fixed materialized code root')
    _exact(bundle['derived_root'], case_root + '/derived', 'fixed materialized derived root')
    plan = bundle['plan']; freeze = bundle['complete_freeze']; proof = bundle['public_preread']
    activation = bundle['activation_receipt']
    _validate_plan(plan); _validate_freeze(freeze)
    for key, value in (('plan_sha256', plan), ('complete_freeze_sha256', freeze),
            ('public_preread_sha256', proof), ('activation_receipt_sha256', activation),
            ('invocation_spending_sha256', bundle['invocation_spending'])):
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
    _validate_activation_receipt(activation, plan, freeze, proof,execution_scope=scope)
    _spending_module().verify_spend_witness(bundle['invocation_spending'], activation,
        execution_scope=scope, ledger_root=plan['invocation_ledger_root'])
    if plan['code_files'].get(CUSTODY_SOURCE) != CUSTODY_IMPLEMENTATION_PIN:
        raise ValueError('Prospective custody source differs from independently reviewed implementation pin')
    for path, wanted in plan['code_files'].items():
        hashes = freeze['input_sha256s'] if path.startswith('tests/') else freeze['code_sha256s']
        if hashes.get(path) != wanted['sha256']:
            raise ValueError('Complete original freeze omitted prospective material/test source pin: ' + path)
    for name, wanted in plan['runtime_executables'].items():
        if freeze['executables'][name]['resolved'] != wanted['path'] or freeze['runtime_sha256s'].get(wanted['path']) != wanted['sha256']:
            raise ValueError('Original freeze does not bind prospective executable: ' + name)
    return case_root


def _role_roots(bundle, role, ordinal):
    scope = _absolute(bundle['execution_scope'])
    if role in WHOLE_ROLES:
        if ordinal is not None or bundle['case_ordinal'] is not None:
            raise ValueError('Whole-worker ordinal must be exactly None')
        return scope, scope + '/frozen-code', scope + '/derived'
    ordinal = _ordinal(ordinal)
    if type(bundle['case_ordinal']) is not int or bundle['case_ordinal'] != ordinal:
        raise ValueError('Exact per-case worker ordinal required')
    case = scope + f'/cases/case{ordinal:02d}'
    return case, case + '/frozen-code', case + '/derived'


def _file_descriptor(value, expected_path, label):
    if type(value) is not dict or set(value) != {'path', 'bytes', 'sha256'}:
        raise ValueError('Exact role phase file descriptor required: ' + label)
    _exact(_absolute(value['path']), expected_path, 'fixed role input ' + label)
    if type(value['bytes']) is not int or not 0 < value['bytes'] <= ORIGINAL_LIMITS['case_storage_bytes']:
        raise ValueError('Bounded exact positive role input byte count required: ' + label)
    _sha(value['sha256'], label)


def _phase_paths(bundle):
    role = bundle['role']; ordinal = bundle['case_ordinal']
    root, _, _ = _role_roots(bundle, role, ordinal)
    common = {'prepared_json': root + '/prepared.json'}
    if role == 'caller': return common
    if role == 'command': return common
    if role == 'lossless-project':
        return {**common, 'arguments_json': root + '/project-arguments.json',
            'caller_transcript': root + '/caller-result.json',
            'preparation_bundle': root + '/worker-admission.json'}
    if role == 'lossless-verify-retained':
        return {**common, 'arguments_json': root + '/projection-verify-arguments.json',
            'projection': root + '/public-evidence/caller-transcript-compact-lossless.json',
            'source_wire': root + '/store/items/request-000001/part',
            'deterministic_source': root + '/deterministic-source.bin',
            'preparation_bundle': root + '/worker-admission.json'}
    common = {'plan_json': root + '/plan.json', 'freeze_json': root + '/complete-freeze.json',
              'preread_json': root + '/public-preread.json'}
    if role == 'verifier': common['compact_input_plan'] = root + '/compact-input-plan.json'
    return common


def _validate_bundle(bundle, *, ordinal, role=None):
    if type(bundle) is not dict: raise ValueError('Exact worker admission bundle required')
    if bundle.get('schema') == SCHEMA:
        if role not in (None, 'prepare'): raise ValueError('Preparation bundle cannot be relabeled as another role')
        return _validate_prepare_bundle(bundle, ordinal=ordinal)
    if bundle.get('schema') != ROLE_SCHEMA or set(bundle) != BUNDLE_KEYS | {'role', 'phase_inputs'}:
        raise ValueError('Exact versioned worker role bundle required')
    selected = bundle['role']
    if type(selected) is not str or selected not in CASE_ROLES | WHOLE_ROLES or role not in (None, selected):
        raise ValueError('Exact declared worker role required')
    if bundle['namespace'] != NAMESPACE: raise ValueError('Role bundle namespace differs')
    root, code, derived = _role_roots(bundle, selected, ordinal)
    _exact(bundle['code_root'], code, 'fixed role materialized code root')
    _exact(bundle['derived_root'], derived, 'fixed role materialized derived root')
    # Reuse unchanged V1 plan/freeze/preread checks with internal layout only;
    # the actual V2 paths above remain separately bound to the outer bundle.
    surrogate = {key: bundle[key] for key in BUNDLE_KEYS}
    surrogate.update(schema=SCHEMA, case_ordinal=0 if selected in WHOLE_ROLES else ordinal,
        code_root=bundle['execution_scope'] + f'/cases/case{0 if selected in WHOLE_ROLES else ordinal:02d}/frozen-code',
        derived_root=bundle['execution_scope'] + f'/cases/case{0 if selected in WHOLE_ROLES else ordinal:02d}/derived')
    _validate_prepare_bundle(surrogate, ordinal=surrogate['case_ordinal'])
    inputs = bundle['phase_inputs']; paths = _phase_paths(bundle)
    required = set(paths) | ({'label', 'command', 'source_wire'} if selected == 'command'
        else {'prepared_cases'} if selected == 'verifier' else set())
    if type(inputs) is not dict or set(inputs) != required:
        raise ValueError('Exact role-specific phase input inventory required')
    if selected == 'command':
        label = inputs['label']; command = inputs['command']
        if type(label) is not str or not re.fullmatch('command-(?:[0-9]|[12][0-9]|3[0-7]|tail)', label):
            raise ValueError('Exact frozen source-reader or tail command label required')
        if type(command) is not str or not command or len(command.encode()) > 96*1024:
            raise ValueError('Bounded exact command literal required')
        if label == 'command-tail':
            if inputs['source_wire'] is not None:
                raise ValueError('Tail command cannot supply a source-reader wire input')
        else:
            _file_descriptor(inputs['source_wire'], root + '/store/items/request-000001/part', 'source_wire')
    for name, path in paths.items(): _file_descriptor(inputs[name], path, name)
    if selected == 'verifier':
        if type(inputs['prepared_cases']) is not list or len(inputs['prepared_cases']) != 8:
            raise ValueError('Exact eight prepared verifier input descriptors required')
        for index, value in enumerate(inputs['prepared_cases']):
            _file_descriptor(value, root + f'/cases/case{index:02d}/prepared.json', 'verifier prepared case')
    return root


def build_role_admission_bundle(plan, complete_freeze, public_preread, activation_receipt, *, role,
        execution_scope, ordinal=None, phase_inputs, invocation_spending=None):
    """Return a separate pinned phase snapshot, never mutate prior bundles."""
    if role not in CASE_ROLES | WHOLE_ROLES: raise ValueError('Known non-preparation worker role required')
    scope = _absolute(execution_scope)
    base = build_admission_bundle(plan, complete_freeze, public_preread, activation_receipt,
        execution_scope=scope, ordinal=0 if role in WHOLE_ROLES else _ordinal(ordinal),
        invocation_spending=invocation_spending)
    root = scope if role in WHOLE_ROLES else scope + f'/cases/case{ordinal:02d}'
    base.update(schema=ROLE_SCHEMA, role=role, case_ordinal=ordinal,
        code_root=root + '/frozen-code', derived_root=root + '/derived', phase_inputs=phase_inputs)
    _validate_bundle(base, ordinal=ordinal, role=role)
    return json.loads(canonical(base))


def worker_role_layout(bundle, *, role=None, ordinal=None):
    role = bundle.get('role', 'prepare') if role is None else role
    if role not in WHOLE_ROLES and ordinal is None: ordinal = bundle.get('case_ordinal')
    root = _validate_bundle(bundle, ordinal=ordinal, role=role)
    inputs = bundle.get('phase_inputs', {})
    label = inputs.get('label') if role == 'command' else None
    receipt = root + ('/whole-control-supervisor' if role == 'control'
        else '/verifier-supervisor' if role == 'verifier'
        else '/' + label + '-supervisor' if role == 'command'
        else '/' + ('preparation' if role == 'prepare' else role) + '-supervisor')
    bundle_name = 'worker-admission.json' if role == 'prepare' else (label if role == 'command' else role) + '-admission.json'
    return {'worker_scope': root, 'receipt_scope': receipt, 'shared_storage_root': root,
        'bundle_path': root + '/' + bundle_name,
        'runtime_name': 'node' if role in ('caller', 'lossless-project', 'lossless-verify-retained') else 'python',
        'command_label': label, 'role': role, 'ordinal': ordinal,
        'seconds_limit': 4800 if role in WHOLE_ROLES else 120 if role == 'command' else 600,
        'shared_storage_limit_bytes': ORIGINAL_LIMITS['run_storage_bytes'] if role in WHOLE_ROLES else ORIGINAL_LIMITS['case_storage_bytes']}


def build_admission_bundle(plan, complete_freeze, public_preread, activation_receipt, *, execution_scope, ordinal,
        invocation_spending=None):
    """Return metadata only; caller retains canonical(bundle)+newline bytes."""
    scope = _absolute(execution_scope); ordinal = _ordinal(ordinal)
    case_root = scope + f'/cases/case{ordinal:02d}'
    bundle = {'schema': SCHEMA, 'namespace': NAMESPACE, 'case_ordinal': ordinal,
        'execution_scope': scope, 'code_root': case_root + '/frozen-code', 'derived_root': case_root + '/derived',
        'plan': plan, 'complete_freeze': complete_freeze, 'public_preread': public_preread,
        'activation_receipt': activation_receipt,
        'invocation_spending': invocation_spending,
        'plan_sha256': hashlib.sha256(canonical(plan)).hexdigest(),
        'complete_freeze_sha256': hashlib.sha256(canonical(complete_freeze)).hexdigest(),
        'public_preread_sha256': hashlib.sha256(canonical(public_preread)).hexdigest(),
        'activation_receipt_sha256': hashlib.sha256(canonical(activation_receipt)).hexdigest(),
        'invocation_spending_sha256': hashlib.sha256(canonical(invocation_spending)).hexdigest()}
    _validate_bundle(bundle, ordinal=ordinal)
    return json.loads(canonical(bundle))


def bundle_bytes(bundle):
    """Exactly these retained bytes, including newline, are the argv digest."""
    if type(bundle) is not dict: raise ValueError('Worker bundle object required')
    _validate_bundle(bundle, ordinal=bundle.get('case_ordinal'))
    return canonical(bundle) + b'\n'


def expected_worker_argv(bundle, bundle_path, *, ordinal, expected_bundle_sha256, role='prepare'):
    if role not in ROLES: raise ValueError('Known exact worker role required')
    case_root = _validate_bundle(bundle, ordinal=ordinal, role=role)
    digest = _sha(expected_bundle_sha256, 'independently retained exact bundle bytes')
    path = _absolute(bundle_path)
    name = 'worker-admission.json' if role == 'prepare' else (
        bundle['phase_inputs']['label'] + '-admission.json' if role == 'command' else role + '-admission.json')
    _exact(path, case_root + '/' + name, 'fixed role admission bundle path')
    python = bundle['plan']['runtime_executables']['python']['path']
    if role == 'prepare':
        case = bundle['plan']['cases'][ordinal]
        return [python, '-I', '-S', '-B', case_root + '/derived/prepare.py',
                case_root, python, NAMESPACE, str(ordinal), case['archive_prefix'], path, digest]
    node = bundle['plan']['runtime_executables']['node']['path']; inputs = bundle['phase_inputs']
    if role == 'caller': return [node, bundle['derived_root'] + '/fresh-caller.js', '--caller', case_root, path, digest]
    if role == 'command':
        return [python, '-I', '-S', '-B', bundle['code_root'] + '/' + FIXTURE,
                '--exec-command-child', case_root, inputs['label'], inputs['command'], path, digest]
    if role in ('lossless-project', 'lossless-verify-retained'):
        return [node, bundle['derived_root'] + '/lossless-helper.js',
            '--resource-project' if role == 'lossless-project' else '--resource-verify-retained',
            inputs['arguments_json']['path'], path, digest]
    return [python, '-I', '-S', '-B', bundle['code_root'] + '/' + FIXTURE,
            '--control-worker' if role == 'control' else '--verifier-worker', case_root, path, digest]


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


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('Duplicate phase JSON property refused')
        result[key] = value
    return result


def _json_value(raw):
    def nonfinite(value): raise ValueError('Nonfinite role phase JSON refused')
    return json.loads(raw, object_pairs_hook=_unique_pairs, parse_constant=nonfinite)


def _phase_file(descriptor, *, json_input=False):
    actual, raw = read_pinned_file(descriptor['path'],
        maximum=MAX_JSON_BYTES if json_input else ORIGINAL_LIMITS['case_storage_bytes'], retain=json_input)
    _exact(actual, {key: descriptor[key] for key in ('bytes', 'sha256')}, 'current role input ' + descriptor['path'])
    return _json_value(raw) if json_input else actual


def _prepared_identity(prepared, plan, case_root, ordinal):
    fields = {'schema', 'python', 'scope', 'control_case_identity', 'source_domain_hex',
        'source_bytes', 'source_sha256', 'archive_bytes', 'archive_files',
        'actual_source_read_fragments', 'conservative_source_read_fragment_ceiling',
        'manifest_bytes', 'request_view', 'reads', 'files'}
    if type(prepared) is not dict or set(prepared) != fields or prepared.get('schema') != 'radio-native-v2-offline-maximum-prepared-v1':
        raise ValueError('Pinned actual prepared metadata required')
    _exact(prepared.get('scope'), case_root, 'prepared scope')
    _exact(prepared.get('python'), plan['runtime_executables']['python']['path'], 'prepared Python')
    _exact(prepared.get('source_domain_hex'), source_domain(ordinal).hex(), 'prepared source domain')
    source = _sha(prepared.get('source_sha256'), 'prepared deterministic source')
    expected = {'namespace': NAMESPACE, 'case_ordinal': ordinal,
        'source_case_id': plan['cases'][ordinal]['source_case_id'],
        'source_sha256': source, 'native_case_binding_verified': False}
    expected['engineering_case_binding_sha256'] = hashlib.sha256(canonical(expected)).hexdigest()
    _exact(prepared.get('control_case_identity'), expected, 'prepared outer case identity')
    counts = {key: plan['cases'][ordinal][key] for key in ('source_bytes', 'archive_files', 'archive_bytes')}
    counts.update(actual_source_read_fragments=38, conservative_source_read_fragment_ceiling=39, manifest_bytes=524288)
    for key, count in counts.items():
        if type(prepared.get(key)) is not int or prepared[key] != count:
            raise ValueError('Prepared fixed case metadata allocation differs: ' + key)
    prefix = plan['cases'][ordinal]['archive_prefix']
    expected_files = {prefix + f'/chunk{index:04d}.b64': 1398104 for index in range(26)}
    expected_files.update({prefix + '/manifest.json': 524288, prefix + '/HEAD': 65})
    files = prepared['files']
    if type(files) is not dict or set(files) != set(expected_files):
        raise ValueError('Prepared exact fixed archive paths required')
    for path, amount in expected_files.items():
        pin = files[path]
        if type(pin) is not dict or set(pin) != {'bytes', 'sha256'} or type(pin['bytes']) is not int or pin['bytes'] != amount:
            raise ValueError('Prepared exact fixed archive file byte count required')
        _sha(pin['sha256'], 'prepared archive file ' + path)
    reads = prepared.get('reads'); view = prepared.get('request_view')
    if type(reads) is not list or len(reads) != 38 or type(view) is not dict:
        raise ValueError('Exact prepared source-read inventory and request view required')
    if set(view) != {'schema', 'path', 'source_bytes', 'source_sha256', 'offset', 'bytes',
            'sha256', 'request_prefix', 'request_suffix', 'request_bytes', 'request_sha256'}:
        raise ValueError('Exact prepared request-view fields required')
    _exact(view['schema'], 'radio-native-v2-existing-request-view-v1', 'prepared request-view schema')
    _exact(view.get('path'), case_root + '/store/items/request-000001/part', 'prepared wire path')
    _sha(view.get('source_sha256'), 'prepared source wire')
    _sha(view['sha256'], 'prepared parameter bytes'); _sha(view['request_sha256'], 'prepared complete request')
    _exact(view['request_prefix'], '{"tool":"mcp__codex_apps__github_create_tree","arguments":', 'prepared request prefix')
    _exact(view['request_suffix'], '}', 'prepared request suffix')
    if type(view['request_bytes']) is not int or view['request_bytes'] != view['bytes'] + len(view['request_prefix'].encode()) + 1:
        raise ValueError('Exact prepared complete request byte count required')
    for key in ('source_bytes', 'offset', 'bytes'):
        if type(view.get(key)) is not int or view[key] < 0:
            raise ValueError('Exact prepared request-view integer fields required')
    if not 0 < view['bytes'] <= view['source_bytes'] <= ORIGINAL_LIMITS['case_request_bytes'] or view['offset'] + view['bytes'] > view['source_bytes']:
        raise ValueError('Prepared request-view range bounds differ')
    cursor = view['offset']
    for index, row in enumerate(reads):
        if type(row) is not dict or set(row) != {'ordinal', 'tool', 'arguments', 'path', 'offset', 'bytes',
                'source_sha256', 'output_sha256', 'response_reserved_bytes'} or type(row.get('ordinal')) is not int or row['ordinal'] != index or row.get('tool') != 'exec_command':
            raise ValueError('Exact ordered prepared source-read ordinal required')
        _exact(row.get('path'), view['path'], 'prepared read source path')
        _exact(row.get('source_sha256'), view['source_sha256'], 'prepared read source hash')
        if type(row.get('offset')) is not int or row['offset'] != cursor or type(row.get('bytes')) is not int or not 0 < row['bytes'] <= MIB - 65536:
            raise ValueError('Prepared read contiguous range binding differs')
        _sha(row.get('output_sha256'), 'prepared read output')
        if type(row['response_reserved_bytes']) is not int or not row['bytes']+8192 <= row['response_reserved_bytes'] <= ORIGINAL_LIMITS['case_response_bytes']:
            raise ValueError('Prepared exact bounded reader response reservation required')
        if type(row.get('arguments')) is not dict or set(row['arguments']) != {'cmd', 'max_output_tokens', 'yield_time_ms'}:
            raise ValueError('Exact prepared reader tool arguments required')
        _exact(row['arguments'].get('max_output_tokens'), 400000, 'reader output-token bound')
        _exact(row['arguments'].get('yield_time_ms'), 1000, 'reader yield interval')
        try: actual = shlex.split(row['arguments']['cmd'])
        except (TypeError, ValueError) as failure: raise ValueError('Prepared reader argv cannot be parsed') from failure
        _exact(actual, [prepared['python'], '-I', '-S', '-B', '-c', SOURCE_READER,
            view['path'], str(row['offset']), str(row['bytes'])], 'frozen prepared reader argv')
        cursor += row['bytes']
    if cursor != view['offset'] + view['bytes']:
        raise ValueError('Prepared readers must cover the exact request-view range')
    return expected


def _embedded_case_identity(value, identity):
    """Check every explicit identity carried by a compact terminal envelope."""
    if type(value) is dict:
        for key, item in value.items():
            if key == 'control_case_identity': _exact(item, identity, 'retained terminal case identity')
            elif type(item) in (dict, list): _embedded_case_identity(item, identity)
            elif key in ('output', 'response_json') and type(item) is str:
                for line in item.splitlines():
                    try: parsed = _json_value(line)
                    except (ValueError, TypeError): continue
                    _embedded_case_identity(parsed, identity)
    elif type(value) is list:
        for item in value: _embedded_case_identity(item, identity)


def validate_command_phase(plan, prepared, *, case_root, label, command):
    """Reader/tail semantics only; caller separately pins current phase files."""
    root = _absolute(case_root)
    if type(label) is not str or not re.fullmatch('command-(?:[0-9]|[12][0-9]|3[0-7]|tail)', label):
        raise ValueError('Exact source-reader/tail label required')
    if type(command) is not str or len(command.encode()) > 96*1024:
        raise ValueError('Bounded exact command literal required')
    try: argv = shlex.split(command)
    except ValueError as failure: raise ValueError('Exact isolated command argv required') from failure
    python = plan['runtime_executables']['python']['path']
    if label != 'command-tail':
        index = int(label.removeprefix('command-')); row = prepared['reads'][index]
        _exact(command, row['arguments']['cmd'], 'selected exact prepared reader command')
        _exact(argv, [python, '-I', '-S', '-B', '-c', SOURCE_READER, row['path'],
                     str(row['offset']), str(row['bytes'])], 'selected isolated reader argv')
        return {'kind': 'prepared_source_reader', 'reader_ordinal': index, 'selected_output_sha256': row['output_sha256']}
    if len(argv) != 20:
        raise ValueError('Exact pinned caller-tail bootstrap argv required')
    helper = root + '/frozen-code/scripts/radio_native_v2_caller_tail.py'
    _exact(argv[:8], [python, '-I', '-S', '-B', '-c', TAIL_BOOTSTRAP, helper,
        plan['code_files']['scripts/radio_native_v2_caller_tail.py']['sha256']], 'pinned tail bootstrap/helper source')
    _exact(argv[8::2], ['--destination', '--payload-base64', '--expected-bytes',
        '--expected-sha256', '--client-sha256', '--terminal-ordinal'], 'exact tail option sequence')
    _exact(argv[9], root + '/caller-tail.json', 'exact tail destination')
    encoded = argv[11]
    if len(encoded) > 62*1024: raise ValueError('Bounded tail base64 required')
    try: payload = base64.b64decode(encoded, validate=True)
    except ValueError as failure: raise ValueError('Canonical tail base64 required') from failure
    if base64.b64encode(payload).decode() != encoded or not 0 < len(payload) <= 62*1024//4*3:
        raise ValueError('Canonical bounded tail payload required')
    if not re.fullmatch('[1-9][0-9]*', argv[13]) or int(argv[13]) != len(payload):
        raise ValueError('Exact tail payload byte count required')
    _exact(_sha(argv[15], 'tail payload'), hashlib.sha256(payload).hexdigest(), 'tail payload hash')
    _sha(argv[17], 'tail client binding')
    if not re.fullmatch('0|[1-9][0-9]*', argv[19]): raise ValueError('Exact tail terminal ordinal required')
    terminal = int(argv[19]); value = _json_value(payload)
    if type(value) is not dict or set(value) != {'schema', 'client_sha256', 'records'} or value['schema'] != 'radio-native-v2-caller-only-tail-v2':
        raise ValueError('Exact compact caller-tail payload schema required')
    if canonical(value) != payload or value['client_sha256'] != argv[17]:
        raise ValueError('Canonical exact tail/client payload binding required')
    rows = value['records']; previous = -1; selected = None
    if type(rows) is not list or not rows: raise ValueError('Retained terminal tail records required')
    for row in rows:
        if type(row) is not dict or set(row) != {'ordinal', 'response_json'} or type(row['ordinal']) is not int or row['ordinal'] <= previous or type(row['response_json']) is not str:
            raise ValueError('Exact ordered retained tail envelopes required')
        envelope = _json_value(row['response_json'])
        if type(envelope) is not dict: raise ValueError('Complete retained tail execution envelope required')
        _embedded_case_identity(envelope, prepared['control_case_identity'])
        if row['ordinal'] == terminal: selected = envelope
        previous = row['ordinal']
    if selected is None or selected.get('isError') is True or type(selected.get('output')) is not str:
        raise ValueError('Exact retained terminal acknowledgement required')
    return {'kind': 'pinned_caller_tail', 'terminal_ordinal': terminal,
            'payload_bytes': len(payload), 'complete_client_binding_independently_recovered': False}


def _read_range_pin(path, offset, amount):
    parent, name = _absolute(path).rsplit('/', 1); directory = _directory(parent); fd = None
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or offset + amount > before.st_size:
            raise ValueError('Exact retained reader range required')
        digest = hashlib.sha256(); used = 0
        while used < amount:
            raw = os.pread(fd, min(65536, amount-used), offset+used)
            if not raw: raise ValueError('Retained reader range truncated')
            digest.update(raw); used += len(raw)
        if _identity(before) != _identity(os.fstat(fd)) or _identity(before) != _identity(os.stat(name, dir_fd=directory, follow_symlinks=False)):
            raise ValueError('Retained reader source changed during range read')
        return {'bytes': used, 'sha256': digest.hexdigest()}
    finally:
        if fd is not None: os.close(fd)
        os.close(directory)


def _absent(path):
    parent, name = _absolute(path).rsplit('/', 1)
    try: directory = _directory(parent)
    except FileNotFoundError: return
    try:
        try: os.stat(name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError: return
        raise ValueError('Existing role output/scope reuse refused: ' + path)
    finally: os.close(directory)


def _large_identity(descriptor, identity):
    """Inspect only the fixed leading schema/identity, never parse a full trace."""
    actual, raw = read_pinned_file(descriptor['path'], maximum=ORIGINAL_LIMITS['case_storage_bytes'], retain_prefix=65536)
    _exact(actual, {key: descriptor[key] for key in ('bytes', 'sha256')}, 'retained caller same-read file/identity pin')
    # A bounded prefix may end inside a later UTF-8 scalar. The identity itself
    # must parse fully in this prefix, hashed in the same stable file read.
    text = codecs.getincrementaldecoder('utf-8')().decode(raw, final=False)
    decoder = json.JSONDecoder(object_pairs_hook=_unique_pairs)
    match = re.match(r'\s*\{\s*"schema"\s*:\s*', text)
    if not match: raise ValueError('Exact original caller schema prefix required')
    schema, end = decoder.raw_decode(text, match.end())
    match = re.match(r'\s*,\s*"control_case_identity"\s*:\s*', text[end:])
    if not match or schema != 'radio-native-v2-compact-eight-input-resource-control-v1':
        raise ValueError('Leading original caller schema/identity required')
    value, _ = decoder.raw_decode(text, end+match.end())
    _exact(value, identity, 'actual leading retained caller identity')


def _validate_role_phase(bundle, *, running_caller=False):
    role = bundle['role']; ordinal = bundle['case_ordinal']; inputs = bundle['phase_inputs']
    root, _, _ = _role_roots(bundle, role, ordinal); plan = bundle['plan']
    values = {}; file_pins = {}
    for name in _phase_paths(bundle):
        json_input = name not in ('caller_transcript', 'source_wire', 'deterministic_source')
        values[name] = _phase_file(inputs[name], json_input=json_input)
        file_pins[name] = {key: inputs[name][key] for key in ('bytes', 'sha256')}
    if role in WHOLE_ROLES:
        for name, key in (('plan_json', 'plan'), ('freeze_json', 'complete_freeze'), ('preread_json', 'public_preread')):
            _exact(values[name], bundle[key], 'current whole-scope ' + name)
        if role == 'control':
            for name in ('control-worker-identity.json', 'cases', 'worker-result.json', 'compact-input-plan.json', 'closed-failure.json'):
                _absent(root + '/' + name)
        else:
            compact = values['compact_input_plan']
            if type(compact) is not dict or set(compact) != {'schema', 'run_id', 'cases'} or compact['schema'] != 'radio-native-v2-compact-retained-run-plan-v1' or compact['run_id'] != NAMESPACE:
                raise ValueError('Exact retained eight-case verifier phase plan required')
            if type(compact['cases']) is not list or len(compact['cases']) != 8:
                raise ValueError('Exactly eight retained verifier phase identities required')
            required = {'ordinal', 'source_case_id', 'source_path', 'bytes', 'sha256',
                'client_peak_rss_bytes', 'other_host_receipt_bytes', 'other_host_receipt_allocated_bytes'}
            logical = allocated = 0; hashes = set()
            for index, case in enumerate(compact['cases']):
                if type(case) is not dict or set(case) != required or type(case.get('ordinal')) is not int or case['ordinal'] != index:
                    raise ValueError('Exact ordered retained verifier source ordinal required')
                _exact(case.get('source_case_id'), plan['cases'][index]['source_case_id'], 'verifier original source-case identity')
                expected_path = root + f'/cases/case{index:02d}/caller-result.json'
                _file_descriptor({key: case[key] for key in ('bytes', 'sha256')} | {'path': case.get('source_path')}, expected_path, 'verifier source')
                descriptor = {'path': expected_path, 'bytes': case['bytes'], 'sha256': case['sha256']}
                _phase_file(descriptor)
                # The trace identity independently joins the current prepared
                # file, not an unexamined source-case string in this plan.
                descriptor_prepared = inputs['prepared_cases'][index]
                identity = _prepared_identity(_phase_file(descriptor_prepared, json_input=True), plan, root + f'/cases/case{index:02d}', index)
                _large_identity(descriptor, identity)
                if case['sha256'] in hashes: raise ValueError('Retained verifier hash replay refused')
                hashes.add(case['sha256'])
                for key in ('client_peak_rss_bytes', 'other_host_receipt_bytes', 'other_host_receipt_allocated_bytes'):
                    if type(case[key]) is not int or case[key] < 0:
                        raise ValueError('Exact nonnegative verifier resource integers required')
                if not 0 < case['client_peak_rss_bytes'] <= ORIGINAL_LIMITS['rss_bytes']:
                    raise ValueError('Original verifier caller RSS bound exceeded')
                reserved = case['bytes'] + 65536
                logical_case = reserved + case['other_host_receipt_bytes']
                allocated_case = reserved + case['other_host_receipt_allocated_bytes']
                if max(logical_case, allocated_case) > ORIGINAL_LIMITS['case_storage_bytes']:
                    raise ValueError('Original verifier case storage reservation exceeded')
                logical += logical_case; allocated += allocated_case
            if max(logical, allocated) > ORIGINAL_LIMITS['run_storage_bytes'] or len(canonical(compact))+1 > 16384:
                raise ValueError('Original verifier whole storage/metadata reservation exceeded')
            for name in ('verifier-identity.json', 'compact-receipt', 'verifier-timing.json'):
                _absent(root + '/' + name)
        return {'phase_input_pins': file_pins, 'role_identity_metadata_checked': True,
                'full_source_domain_content_verified': False,
                'complete_retained_transport_semantics_verified': False}
    prepared = values['prepared_json']; identity = _prepared_identity(prepared, plan, root, ordinal)
    extra = {'phase_input_pins': file_pins, 'role_identity_metadata_checked': True,
             'full_source_domain_content_verified': False,
             'complete_retained_transport_semantics_verified': False}
    if role == 'caller':
        if not running_caller:
            for name in ('caller-start.json', 'caller-result.json', 'caller-summary.json', 'caller-tail.json',
                         'rss-observation-request.json', 'rss-observation.json'):
                _absent(root + '/' + name)
    elif role == 'command':
        _absent(root + '/command-observations/' + inputs['label'] + '-identity.json')
        extra['command_binding'] = validate_command_phase(plan, prepared,
            case_root=root, label=inputs['label'], command=inputs['command'])
        if inputs['label'] == 'command-tail': _absent(root + '/caller-tail.json')
        else:
            wire = inputs['source_wire']; view = prepared['request_view']
            _exact({key: wire[key] for key in ('path', 'bytes', 'sha256')},
                {'path': view['path'], 'bytes': view['source_bytes'], 'sha256': view['source_sha256']}, 'command wire/prepared join')
            _phase_file(wire)
            row = prepared['reads'][int(inputs['label'].removeprefix('command-'))]
            _exact(_read_range_pin(wire['path'], row['offset'], row['bytes']),
                {'bytes': row['bytes'], 'sha256': row['output_sha256']}, 'current selected source-reader output')
    else:
        recipe = [root, plan['runtime_executables']['python']['path'], NAMESPACE, str(ordinal),
            plan['cases'][ordinal]['archive_prefix'], root + '/worker-admission.json', inputs['preparation_bundle']['sha256']]
        prior_bundle = load_bundle(inputs['preparation_bundle']['path'],
            expected_bundle_sha256=inputs['preparation_bundle']['sha256'])
        _validate_prepare_bundle(prior_bundle, ordinal=ordinal)
        for key in ('plan', 'complete_freeze', 'public_preread', 'activation_receipt', 'invocation_spending'):
            _exact(prior_bundle[key], bundle[key], 'preparation recipe evidence binding ' + key)
        options = values['arguments_json']
        if role == 'lossless-project':
            expected = {'fullPath': root + '/caller-result.json', 'preparedPath': root + '/prepared.json',
                'recipePath': root + '/derived/prepare.py',
                'projectionPath': root + '/public-evidence/caller-transcript-compact-lossless.json',
                'recipeArguments': recipe, 'identityPath': root + '/lossless-project-identity.json'}
            _large_identity(inputs['caller_transcript'], identity)
            _absent(expected['projectionPath']); _absent(expected['identityPath'])
        else:
            view = prepared['request_view']
            _exact(file_pins['source_wire'], {'bytes': view['source_bytes'], 'sha256': view['source_sha256']}, 'retained wire/prepared source pin')
            _exact(file_pins['deterministic_source'], {'bytes': prepared['source_bytes'], 'sha256': prepared['source_sha256']}, 'retained deterministic payload/prepared pin')
            expected = {'projectionPath': root + '/public-evidence/caller-transcript-compact-lossless.json',
                'recipePath': root + '/derived/prepare.py', 'retainedSourcePath': view['path'],
                'retainedPayloadPath': root + '/deterministic-source.bin',
                'auditPath': root + '/public-evidence/reconstruction-audit.json',
                'python': plan['runtime_executables']['python']['path'], 'identityPath': root + '/lossless-verify-identity.json'}
            projection = values['projection']; regeneration = projection.get('regeneration', {}) if type(projection) is dict else {}
            if type(projection) is not dict or projection.get('schema') != 'radio-native-v2-compact-eight-case-lossless-projection-v1' or projection.get('fixture_only') is not True or projection.get('execution_authorized') is not False or projection.get('scientific_execution_authorized') is not False:
                raise ValueError('Exact non-authorizing retained projection phase required')
            for key in ('native_case_reservations', 'native_case_executions', 'scientific_cases_run',
                    'rng_draws', 'telescope_reads', 'actual_connector_calls', 'actual_functions_sdk_calls', 'network_fetches', 'automatic_retry'):
                _exact(projection.get(key), AUTHORITY[key], 'retained projection authority ' + key)
            _exact(regeneration.get('prepared'), prepared, 'projection retained prepared metadata')
            _exact(regeneration.get('recipe_arguments'), recipe, 'projection frozen recipe arguments')
            _exact({'bytes': regeneration.get('recipe_bytes'), 'sha256': regeneration.get('recipe_sha256')}, plan['derived_code']['prepare.py'], 'projection exact recipe source pin')
            _exact(projection.get('transcript', {}).get('control_case_identity'), identity, 'projection transcript identity')
            _absent(expected['auditPath']); _absent(expected['identityPath'])
        _exact(options, expected, 'exact frozen lossless options JSON')
    return extra


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
    return _validate_worker_admission(bundle_path, role=role, ordinal=ordinal, argv=argv,
        environment=environment, expected_bundle_sha256=expected_bundle_sha256)


def validate_running_caller_admission(bundle_path, *, ordinal, argv, environment,
        expected_bundle_sha256):
    """Recheck a caller snapshot for its command wrapper, after caller start.

    This is not a prelaunch admission: caller output absence is not checked.
    The wrapper must independently map and check its live Node parent identity.
    """
    return _validate_worker_admission(bundle_path, role='caller', ordinal=ordinal, argv=argv,
        environment=environment, expected_bundle_sha256=expected_bundle_sha256, running_caller=True)


def _validate_worker_admission(bundle_path, *, role, ordinal, argv, environment,
        expected_bundle_sha256, running_caller=False):
    if type(argv) is not list or any(type(item) is not str for item in argv):
        raise ValueError('Exact complete worker argv string list required')
    if type(environment) is not dict:
        raise ValueError('Exact complete child environment dictionary required')
    _exact(environment, CHILD_ENVIRONMENT, 'complete minimal child environment')
    bundle = load_bundle(_absolute(bundle_path), expected_bundle_sha256=expected_bundle_sha256)
    expected = expected_worker_argv(bundle, bundle_path, ordinal=ordinal,
        expected_bundle_sha256=expected_bundle_sha256, role=role)
    _exact(argv, expected, 'exact preparation worker argv' if role == 'prepare' else 'exact ' + role + ' worker argv')
    plan = bundle['plan']; code_root = bundle['code_root']; derived_root = bundle['derived_root']
    layout = worker_role_layout(bundle, role=role, ordinal=ordinal)
    if role == 'prepare':
        case_directory = _directory(layout['worker_scope'])
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
    _exact(str(Path(sys.executable).resolve()), plan['runtime_executables']['python']['path'], 'actual checker Python executable')
    for name in {'python', layout['runtime_name']}:
        executable = plan['runtime_executables'][name]
        if str(Path(executable['path']).resolve()) != executable['path']:
            raise ValueError('Prospective executable path alias refused: ' + name)
        actual, _ = read_pinned_file(executable['path'], sole_link=False)
        _exact(actual, {'bytes': executable['bytes'], 'sha256': executable['sha256']}, 'actual pinned executable bytes ' + name)
    custody = _custody_module()
    manifest,custody_sha256 = _custody_contract(bundle['complete_freeze'],custody)
    custody.validate_material_runtime(manifest,expected_manifest_sha256=custody_sha256)
    phase = _validate_role_phase(bundle, running_caller=running_caller) if role != 'prepare' else {}
    # Reopen exact bundle after all material reads; a valid initial snapshot
    # must not silently become a different admission file during the checks.
    load_bundle(bundle_path, expected_bundle_sha256=expected_bundle_sha256)
    return {'schema': RECEIPT_SCHEMA, 'status': 'LOCAL_SUPPLIED_PREREAD_VALIDATED_EXECUTION_BLOCKED',
        'namespace': NAMESPACE, 'case_ordinal': ordinal,
        'source_case_id': plan['cases'][ordinal]['source_case_id'] if ordinal is not None else None,
        'source_domain_hex': source_domain(ordinal).hex() if ordinal is not None else None,
        'archive_prefix': plan['cases'][ordinal]['archive_prefix'] if ordinal is not None else None, 'role': role,
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
        'runtime_custody_manifest_sha256':custody_sha256,
        'material_runtime_custody_rechecked':True,
        'activation_only_git_used_by_worker':False,
        'activation_only_git_aliases_enumerated_by_worker':False,
        'fresh_preparation_output_names_absent': role == 'prepare',
        'fresh_role_output_names_absent': not running_caller,
        'running_caller_snapshot_recheck': running_caller,
        'live_caller_parent_identity_independently_verified': False,
        'worker_role_layout': layout,
        'loaded_validator_code': loaded_self,
        'complete_expected_runtime_closure_verified': False,
        'current_parent_environment_verified': False,
        'runtime_and_supplement_join_verified': False,
        'fixture_execution_guard_still_required': True,
        'pipeline_integration_qualified': False, 'large_source_generation_admitted': False,
        'all_original_execution_blockers_closed': False,
        'checks_remain_subject_to_postcheck_mutation': True, **phase, **AUTHORITY}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true', required=True)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--bundle-sha256', required=True)
    parser.add_argument('--role', choices=sorted(ROLES), default='prepare')
    parser.add_argument('--ordinal', type=int)
    parser.add_argument('--worker-argv-json', help='Optional actual complete argv JSON; absent means metadata-only expected argv')
    args = parser.parse_args()
    path = _absolute(args.bundle)
    bundle = load_bundle(path, expected_bundle_sha256=args.bundle_sha256)
    argv = expected_worker_argv(bundle, path, ordinal=args.ordinal,
        expected_bundle_sha256=args.bundle_sha256, role=args.role)
    if args.worker_argv_json is not None: argv = _json_value(args.worker_argv_json)
    result = validate_worker_admission(path, role=args.role, ordinal=args.ordinal, argv=argv,
        environment=dict(os.environ), expected_bundle_sha256=args.bundle_sha256)
    print(canonical(result).decode())


if __name__ == '__main__':
    main()
