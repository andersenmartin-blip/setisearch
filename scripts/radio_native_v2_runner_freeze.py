#!/usr/bin/env python3
"""Prospective native-v2 runner/broker file freeze, with no execution authority.

Unlike the historical preparation freeze, this inventory includes JavaScript,
the host adapter, Git/Node executables and their measured local ELF closure.
It never reserves cases, constructs a generator or calls a publication tool.
An immutable Git readback proves local file identity only; it cannot establish
that the future runner is connected to a qualified external tool transport.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys

import numpy as np

from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater import whole_cadence_runtime_radio as python_runtime


SCHEMA = 'radio-native-v2-runner-broker-runtime-freeze-v1'
FREEZE_KIND = 'COMPLETE_RUNNER_BROKER_RUNTIME'
NAMESPACE = 'radio-native-v2-engineering-20260930a'
HOST_ADAPTER = 'scripts/radio_native_v2_broker_host.js'
SELF = 'scripts/radio_native_v2_runner_freeze.py'
CODE_SUFFIXES = frozenset(('.py', '.js', '.mjs', '.cjs', '.c', '.h', '.sh'))
ENVIRONMENT_KEYS = (
    'PATH', 'PYTHONPATH', 'PYTHONHOME', 'PYTHONSAFEPATH', 'PYTHONNOUSERSITE',
    'NODE_OPTIONS', 'NODE_PATH', 'NODE_ICU_DATA', 'LD_LIBRARY_PATH', 'LD_PRELOAD',
    'OPENSSL_CONF', 'OPENSSL_MODULES', 'SSL_CERT_FILE', 'SSL_CERT_DIR',
    'GIT_EXEC_PATH', 'GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_SYSTEM',
    'GIT_CONFIG_GLOBAL', 'GIT_CONFIG_COUNT', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
    'GIT_OBJECT_DIRECTORY', 'GIT_NAMESPACE',
)
DISABLED = (
    'reservation_authorized', 'rng_authorized', 'execution_authorized',
    'scientific_execution_authorized', 'restart_authorized',
    'transport_integration_qualified',
)


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _sha(value, label):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Exact SHA256 required: ' + label)
    return value


def _path(value):
    if (not isinstance(value, str) or not value or '\\' in value
            or re.search(r'[\x00-\x1f\x7f]', value)
            or PurePosixPath(value).is_absolute()
            or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Canonical repository-relative file path required')
    return value


def _local_file(root, value):
    path = Path(root) / _path(value)
    if not path.is_file() or not path.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('Missing/escaping local freeze dependency: ' + value)
    return path


def environment_fingerprints():
    # Hashes avoid recording configuration/credential values in public evidence.
    return {name: (hashlib.sha256(os.environ[name].encode()).hexdigest()
                   if name in os.environ else None) for name in ENVIRONMENT_KEYS}


def repository_inventory(root):
    root = Path(root).resolve()
    present = {str(p.relative_to(root))
               for folder in ('src/seti_repeater', 'scripts')
               for p in (root / folder).rglob('*')
               if p.is_file() and p.suffix in CODE_SUFFIXES
               and '__pycache__' not in p.parts}
    tracked = subprocess.check_output(
        ['git', 'ls-files', '-z', '--', 'src/seti_repeater', 'scripts'], cwd=root
    ).decode().split('\0')
    missing = {p for p in tracked if Path(p).suffix in CODE_SUFFIXES} - present
    if missing:
        raise ValueError('Tracked runner/broker code missing: ' + ','.join(sorted(missing)))
    if HOST_ADAPTER not in present or SELF not in present:
        raise ValueError('Complete freeze requires helper and JavaScript host adapter')
    for path in present:
        _local_file(root, path)
    return sorted(present)


def _elf(path):
    with Path(path).open('rb') as source:
        return source.read(4) == b'\x7fELF'


def elf_dependencies(paths):
    """Resolve all available transitive ELF files; unresolved libraries stop."""
    pending = {Path(p).resolve() for p in paths if _elf(p)}
    checked = set()
    while pending:
        path = min(pending)
        pending.remove(path)
        if path in checked:
            continue
        checked.add(path)
        result = subprocess.run(['ldd', str(path)], capture_output=True,
                                text=True, timeout=10)
        output = result.stdout + result.stderr
        static = ('statically linked' in output or 'not a dynamic executable' in output)
        if 'not found' in output or (result.returncode and not static):
            raise ValueError('Unresolved/uninspectable Git/Node ELF dependency: ' + str(path))
        for line in output.splitlines():
            match = re.search(r'(?:=>\s*)?(/\S+)\s+\(', line)
            if match:
                dependency = Path(match.group(1)).resolve()
                if not dependency.is_file():
                    raise ValueError('Missing ELF dependency: ' + str(dependency))
                if dependency not in checked:
                    pending.add(dependency)
    return sorted(str(path) for path in checked)


def executable_identity(name):
    invocation = sys.executable if name == 'python' else shutil.which(name)
    if not invocation or not Path(invocation).is_file():
        raise ValueError('Required local runtime executable absent: ' + name)
    path = Path(invocation).resolve()
    if name == 'python':
        version = sys.version
    elif name == 'git':
        version = subprocess.check_output([str(path), '--version'], text=True).strip()
    else:
        # Node built-ins, V8, ICU and OpenSSL versions are pinned with the binary.
        version = json.loads(subprocess.check_output(
            [str(path), '-p', 'JSON.stringify(process.versions)'], text=True))
    return {'invocation': str(Path(invocation).absolute()), 'resolved': str(path),
            'sha256': sha_file(path), 'version': version}


def runtime_inventory():
    python_files, unavailable = python_runtime.runtime_inventory()
    executables = {name: executable_identity(name) for name in ('python', 'git', 'node')}
    git_exec_path = Path(subprocess.check_output(
        [executables['git']['resolved'], '--exec-path'], text=True).strip()).resolve()
    if not git_exec_path.is_dir():
        raise ValueError('Installed Git runtime directory absent')
    git_files = sorted({str(p.resolve()) for p in git_exec_path.rglob('*') if p.is_file()})
    external = {record['resolved'] for record in executables.values()} | set(git_files)
    closure = elf_dependencies(external)
    files = sorted(set(python_files) | external | set(closure))
    return {'runtime_file_inventory': files,
            'runtime_sha256s': {path: sha_file(path) for path in files},
            'executables': executables, 'git_exec_path': str(git_exec_path),
            'git_runtime_file_inventory': git_files,
            'git_node_elf_inventory': closure,
            'unavailable_unused_python_extensions': unavailable,
            'python': sys.version, 'numpy': np.__version__}


RUNTIME_FIELDS = (
    'runtime_file_inventory', 'runtime_sha256s', 'executables', 'git_exec_path',
    'git_runtime_file_inventory', 'git_node_elf_inventory',
    'unavailable_unused_python_extensions', 'python', 'numpy',
)


def _immutable_git(root, *arguments, input=None):
    # Even exact object IDs can be substituted through Git replace refs. Missing
    # promisor objects must stop rather than silently initiating a remote fetch.
    environment = {**os.environ, 'GIT_NO_LAZY_FETCH': '1'}
    return subprocess.check_output(
        ['git', '--no-replace-objects', *arguments], cwd=root,
        env=environment, input=input)


def validate_freeze(freeze):
    if (not isinstance(freeze, dict) or freeze.get('schema') != SCHEMA
            or freeze.get('freeze_kind') != FREEZE_KIND
            or freeze.get('mode') != 'PROSPECTIVE_ENGINEERING_ONLY'
            or freeze.get('namespace') != NAMESPACE):
        raise ValueError('Complete prospective runner/broker freeze required; preparation freeze refused')
    if any(freeze.get(name) is not False for name in DISABLED):
        raise ValueError('File freeze cannot grant execution or transport authority')
    if freeze.get('transport_qualification') is not None:
        raise ValueError('A dictionary or file pin cannot qualify actual transport integration')
    inventories = (
        ('repository_code_inventory', 'code_sha256s'),
        ('input_file_inventory', 'input_sha256s'),
        ('runtime_file_inventory', 'runtime_sha256s'),
    )
    for inventory, hashes in inventories:
        if (not isinstance(freeze.get(inventory), list)
                or not isinstance(freeze.get(hashes), dict)
                or freeze[inventory] != sorted(freeze[hashes])):
            raise ValueError('Exact freeze inventory/hash map differs: ' + inventory)
        for path, value in freeze[hashes].items():
            if hashes != 'runtime_sha256s':
                _path(path)
            elif not isinstance(path, str) or not Path(path).is_absolute():
                raise ValueError('Absolute local runtime file required')
            _sha(value, path)
    if not {HOST_ADAPTER, SELF}.issubset(freeze['code_sha256s']):
        raise ValueError('JavaScript host adapter and freeze helper must be pinned')
    overlapping = set(freeze['code_sha256s']) & set(freeze['input_sha256s'])
    if any(freeze['code_sha256s'][p] != freeze['input_sha256s'][p] for p in overlapping):
        raise ValueError('Conflicting code/input identities')
    if set(freeze.get('executables', {})) != {'python', 'git', 'node'}:
        raise ValueError('Python, Git and Node executable identities required')
    for name, record in freeze['executables'].items():
        if (not isinstance(record, dict)
                or set(record) != {'invocation', 'resolved', 'sha256', 'version'}
                or freeze['runtime_sha256s'].get(record['resolved']) != record['sha256']):
            raise ValueError('Executable/runtime identity differs: ' + name)
        if not all(isinstance(record[key], str) and Path(record[key]).is_absolute()
                   for key in ('invocation', 'resolved')):
            raise ValueError('Absolute executable identities required')
        if ((name in ('python', 'git') and not isinstance(record['version'], str))
                or (name == 'node' and not isinstance(record['version'], dict))):
            raise ValueError('Measured executable version required: ' + name)
    for name in ('git_runtime_file_inventory', 'git_node_elf_inventory'):
        if (not isinstance(freeze.get(name), list) or freeze[name] != sorted(set(freeze[name]))
                or not set(freeze[name]).issubset(freeze['runtime_sha256s'])):
            raise ValueError('Incomplete Git/Node runtime inventory: ' + name)
    if not isinstance(freeze.get('git_exec_path'), str) or not Path(freeze['git_exec_path']).is_absolute():
        raise ValueError('Absolute installed Git runtime directory required')
    unavailable = freeze.get('unavailable_unused_python_extensions')
    if (not isinstance(unavailable, dict)
            or not set(unavailable).issubset(freeze['runtime_sha256s'])
            or any(not isinstance(lines, list) or not lines
                   or any(not isinstance(line, str) or 'not found' not in line for line in lines)
                   for lines in unavailable.values())):
        raise ValueError('Measured unused/unavailable Python extension inventory required')
    if not all(isinstance(freeze.get(key), str) and freeze[key] for key in ('python', 'numpy')):
        raise ValueError('Measured Python/NumPy runtime versions required')
    if (not isinstance(freeze.get('environment_fingerprints'), dict)
            or freeze['environment_fingerprints'].keys() != set(ENVIRONMENT_KEYS)):
        raise ValueError('Exact runtime environment fingerprint inventory required')
    for key, value in freeze['environment_fingerprints'].items():
        if value is not None:
            _sha(value, key)
    return freeze


def capture(root, input_paths, *, transport_qualification=None):
    if transport_qualification is not None:
        raise ValueError('Actual transport integration is unqualified; a supplied dictionary is insufficient')
    root = Path(root).resolve()
    code = repository_inventory(root)
    inputs = sorted(set(_path(path) for path in input_paths))
    freeze = {'schema': SCHEMA, 'freeze_kind': FREEZE_KIND,
              'mode': 'PROSPECTIVE_ENGINEERING_ONLY', 'namespace': NAMESPACE,
              **{name: False for name in DISABLED}, 'transport_qualification': None,
              'repository_code_inventory': code,
              'code_sha256s': {path: sha_file(_local_file(root, path)) for path in code},
              'input_file_inventory': inputs,
              'input_sha256s': {path: sha_file(_local_file(root, path)) for path in inputs},
              **runtime_inventory(),
              'environment_fingerprints': environment_fingerprints(),
              'coverage': {
                  'repository': 'source/scripts Python, JavaScript, C headers/source and shell bytes',
                  'python_numpy': 'stdlib/NumPy source/extensions and available ldd closure',
                  'git_node': 'executable bytes, installed Git helper bytes and transitive ELF files; Node built-ins embedded in executable',
                  'external_tool_transport_runtime_frozen': False,
                  'operating_system_kernel_frozen': False,
                  'git_credential_and_network_configuration_frozen': False,
                  'git_script_interpreters_qualified': False,
                  'arbitrary_node_modules_qualified': False,
                  'python_cached_bytecode_execution_qualified': False,
                  'python_import_source_policy_qualified': False,
                  'qualification_scope': 'local file identity only; no integrated external-call proof',
              }}
    return validate_freeze(freeze)


build = capture


def refuse_execution(*args, **kwargs):
    raise ValueError('PROSPECTIVE_NOT_EXECUTABLE: actual runner/tool transport integration is unqualified; freeze grants no reservation or RNG')


@dataclass(frozen=True, init=False, slots=True)
class PublishedFreeze:
    """Verify exact committed bytes and current local runtime, without fetching."""
    root: Path
    commit: str
    path: str
    expected: str
    freeze_identity: str
    published_files: int
    _raw: bytes

    def __init__(self, root, commit, path, expected_sha256):
        root = Path(root).resolve()
        if not isinstance(commit, str) or not re.fullmatch('(?:[0-9a-f]{40}|[0-9a-f]{64})', commit):
            raise ValueError('Immutable full Git commit object ID required')
        path = _path(path)
        expected = _sha(expected_sha256, 'freeze')
        kind = _immutable_git(root, 'cat-file', '-t', commit).strip()
        if kind != b'commit':
            raise ValueError('Immutable Git commit required')
        raw = _immutable_git(root, 'show', commit + ':' + path)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Published complete freeze bytes differ')
        freeze = validate_freeze(json.loads(raw))
        if canonical(freeze) != raw:
            raise ValueError('Canonical published complete freeze required')
        pairs = {**freeze['code_sha256s'], **freeze['input_sha256s']}
        paths = sorted(pairs)
        query = ''.join(commit + ':' + path + '\n' for path in paths).encode()
        output = _immutable_git(root, 'cat-file', '--batch', input=query)
        offset = 0
        for dependency in paths:
            end = output.index(b'\n', offset)
            header = output[offset:end].split()
            offset = end + 1
            if len(header) != 3 or header[1] != b'blob':
                raise ValueError('Published code/input is not a Git blob: ' + dependency)
            size = int(header[2])
            data = output[offset:offset + size]
            offset += size + 1
            if len(data) != size or hashlib.sha256(data).hexdigest() != pairs[dependency]:
                raise ValueError('Published runner/broker dependency differs: ' + dependency)
        if offset != len(output):
            raise ValueError('Grouped immutable Git readback framing differs')
        for key, value in {'root': root, 'commit': commit, 'path': path,
                           'expected': expected, 'freeze_identity': digest(freeze),
                           'published_files': len(paths), '_raw': raw}.items():
            object.__setattr__(self, key, value)

    @property
    def freeze(self):
        """Return a metadata copy; callers cannot change verified state."""
        return json.loads(self._raw)

    def verify(self, manifest=None):
        freeze = validate_freeze(self.freeze)
        if digest(freeze) != self.freeze_identity:
            raise ValueError('Published freeze object changed')
        if manifest is not None and (manifest.get('mode') != 'engineering'
                or manifest.get('namespace') != NAMESPACE
                or manifest.get('execution_binding_sha256') != self.expected):
            raise ValueError('Runner manifest/freeze binding changed')
        if repository_inventory(self.root) != freeze['repository_code_inventory']:
            raise ValueError('Repository runner/broker code inventory changed')
        for path, sha in {**freeze['code_sha256s'], **freeze['input_sha256s']}.items():
            if sha_file(_local_file(self.root, path)) != sha:
                raise ValueError('Local runner/broker code/input changed: ' + path)
        for path, sha in freeze['runtime_sha256s'].items():
            if not Path(path).is_file() or sha_file(path) != sha:
                raise ValueError('Local runtime dependency bytes changed: ' + path)
        # Re-enumerate rather than checking only previously listed paths: new
        # stdlib, NumPy, Git-helper or resolved ELF files also invalidate a pin.
        current_runtime = runtime_inventory()
        for field in RUNTIME_FIELDS:
            if current_runtime[field] != freeze[field]:
                raise ValueError('Local runtime inventory/identity changed: ' + field)
        if environment_fingerprints() != freeze['environment_fingerprints']:
            raise ValueError('Runtime environment changed')
        if sys.version != freeze['python'] or np.__version__ != freeze['numpy']:
            raise ValueError('Python/NumPy runtime versions changed')
        if python_runtime.loaded_files() & set(freeze['unavailable_unused_python_extensions']):
            raise ValueError('Unavailable optional Python extension entered runtime')
        return {'schema': 'radio-native-v2-runner-freeze-verification-v1',
                'freeze_kind': FREEZE_KIND, 'namespace': NAMESPACE,
                'freeze_sha256': self.expected, 'freeze_commit': self.commit,
                'exact_immutable_git_readback_verified': True,
                'remote_publication_verified': False,
                'local_runtime_files_verified': True,
                'published_files': self.published_files,
                'runtime_files': len(freeze['runtime_sha256s']),
                **{name: False for name in DISABLED}}

    require_execution_authority = refuse_execution


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('capture', 'build', 'verify', 'run'))
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--input', action='append', default=[])
    parser.add_argument('--commit')
    parser.add_argument('--freeze-path')
    parser.add_argument('--freeze-sha256')
    args = parser.parse_args()
    if args.action in ('capture', 'build'):
        result = capture(args.root, args.input)
    elif args.action == 'verify':
        result = PublishedFreeze(args.root, args.commit, args.freeze_path, args.freeze_sha256).verify()
    else:
        refuse_execution()
    print(json.dumps(result, sort_keys=True, indent=2))
