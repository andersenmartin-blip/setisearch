#!/usr/bin/env python3
"""Read-only compact-control preparation audit, never execution admission.

Recompute the original freezer's local file scope independently, rather than
trusting a freeze's internally consistent subset. Join the compact supplement
and prospective source pins. This does not close the unfinished public-preread,
worker, whole-process observation, storage, timing, or identity gates. The old
freezer excludes the kernel, tool transport and Git interpreter/configuration
closure; successful local comparisons must not be called complete execution
closure. No source generator, reservation, RNG or scientific case is invoked.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import sysconfig

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
for directory in (REPO / 'src', REPO / 'scripts'):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import numpy as np
import radio_native_v2_runner_freeze as freezer
import radio_native_v2_compact_eight_case_resource_fixture as fixture

SCHEMA = 'radio-native-v2-compact-preparation-audit-v1'
CODE_SUFFIXES = frozenset(('.py', '.js', '.mjs', '.cjs', '.c', '.h', '.sh'))
FREEZE_KEYS = frozenset((
    'schema', 'freeze_kind', 'mode', 'namespace', *freezer.DISABLED,
    'transport_qualification', 'repository_code_inventory', 'code_sha256s',
    'input_file_inventory', 'input_sha256s', *freezer.RUNTIME_FIELDS,
    'environment_fingerprints', 'coverage',
))
COVERAGE = {
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
}
AUTHORITY = {
    'execution_authorized': False, 'reservation_authorized': False,
    'scientific_execution_authorized': False, 'rng_authorized': False,
    'restart_authorized': False, 'large_source_generation_admitted': False,
    'native_case_reservations': 0, 'native_case_executions': 0,
    'scientific_cases_run': 0, 'rng_draws': 0, 'telescope_reads': 0,
    'actual_connector_calls': 0, 'network_fetches': 0,
    'real_public_github_mutations': 0, 'automatic_retry': False,
    'transport_integration_qualified': False,
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _absolute(path):
    value = os.fspath(path)
    if (not isinstance(value, str) or not value.startswith('/') or value == '/'
            or '\\' in value or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value[1:].split('/'))):
        raise ValueError('Canonical absolute audit path required')
    return value


def _relative(path):
    if (not isinstance(path, str) or not path or '\\' in path
            or re.search(r'[\x00-\x1f\x7f]', path)
            or PurePosixPath(path).is_absolute()
            or any(part in ('', '.', '..') for part in path.split('/'))):
        raise ValueError('Canonical repository-relative audit path required')
    return path


def _directory(path):
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in _absolute(path)[1:].split('/'):
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _stable(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_nlink,
            info.st_mtime_ns, info.st_ctime_ns)


def _read(path, *, sole_link=False, maximum=None, retain=False):
    """Walk every ancestor without aliases and hash one stable regular inode.

    Installed external runtimes may legitimately contain Git hardlinks. All
    repository/materialized files and JSON evidence require sole-link inodes.
    """
    value = _absolute(path)
    parent, name = value.rsplit('/', 1)
    directory = _directory(parent) if parent else os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    fd = None
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or (sole_link and before.st_nlink != 1)
                or (maximum is not None and before.st_size > maximum)):
            raise ValueError('Bounded regular audit file without repository hardlink aliases required: ' + value)
        digest = hashlib.sha256(); count = 0; chunks = []
        while True:
            raw = os.read(fd, 65536)
            if not raw:
                break
            count += len(raw)
            if maximum is not None and count > maximum:
                raise ValueError('Bounded audit file exceeded: ' + value)
            digest.update(raw)
            if retain:
                chunks.append(raw)
        after = os.fstat(fd)
        named = os.stat(name, dir_fd=directory, follow_symlinks=False)
        reopened_directory = _directory(parent) if parent else os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        try:
            if (os.fstat(directory).st_dev, os.fstat(directory).st_ino) != (
                    os.fstat(reopened_directory).st_dev, os.fstat(reopened_directory).st_ino):
                raise ValueError('Audit parent directory identity changed: ' + value)
        finally:
            os.close(reopened_directory)
        if _stable(before) != _stable(after) or _stable(after) != _stable(named) or count != after.st_size:
            raise ValueError('Audit file changed during independent read: ' + value)
        return {'bytes': count, 'sha256': digest.hexdigest()}, b''.join(chunks) if retain else None
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory)


def pin(path, *, sole_link=False):
    return _read(path, sole_link=sole_link)[0]


def read_json(path):
    _, raw = _read(path, sole_link=True, maximum=16*1024**2, retain=True)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate audit JSON property refused: ' + key)
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite audit JSON refused')))


def _command(argv, *, cwd=None):
    return subprocess.check_output(argv, cwd=cwd, timeout=30,
        env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'})


def repository_inventory(repo):
    """Re-enumerate actual and tracked code; never accept a named subset."""
    repo = Path(_absolute(repo))
    present = set()
    for folder in ('src/seti_repeater', 'scripts'):
        for path in (repo / folder).rglob('*'):
            if path.suffix in CODE_SUFFIXES and '__pycache__' not in path.parts:
                if path.is_file() or path.is_symlink():
                    relative = _relative(str(path.relative_to(repo)))
                    pin(path, sole_link=True)
                    present.add(relative)
    tracked = _command(['git', '--no-replace-objects', 'ls-files', '-z', '--',
                        'src/seti_repeater', 'scripts'], cwd=repo).decode().split('\0')
    missing = {path for path in tracked if Path(path).suffix in CODE_SUFFIXES} - present
    if missing:
        raise ValueError('Tracked runner/broker code absent from independent inventory: ' + ','.join(sorted(missing)))
    if not {freezer.HOST_ADAPTER, freezer.SELF}.issubset(present):
        raise ValueError('Original freezer and JavaScript host adapter required')
    return sorted(present)


def _loaded_files():
    return {str(Path(value).resolve()) for module in tuple(sys.modules.values())
            if isinstance(value := getattr(module, '__file__', None), str) and Path(value).is_file()}


def _ldd(path, *, allow_missing=False):
    result = subprocess.run(['ldd', str(path)], capture_output=True, text=True, timeout=10)
    output = result.stdout + result.stderr
    static = 'statically linked' in output or 'not a dynamic executable' in output
    missing = [line.strip() for line in result.stdout.splitlines() if 'not found' in line]
    if ((result.returncode and not (static and not allow_missing))
            or (missing and not allow_missing)):
        raise ValueError('Unresolved/uninspectable independently measured ELF: ' + str(path))
    dependencies = set()
    for line in result.stdout.splitlines():
        match = re.search(r'(?:=>\s*)?(/\S+)\s+\(', line)
        if match:
            dependency = Path(match.group(1)).resolve()
            if not dependency.is_file():
                raise ValueError('Missing independently measured ELF dependency: ' + str(dependency))
            dependencies.add(dependency)
    return dependencies, missing


def _python_inventory():
    stdlib = Path(sysconfig.get_path('stdlib'))
    numpy_root = Path(np.__file__).parent
    files = {Path(sys.executable).resolve()}
    for path in stdlib.rglob('*'):
        if 'site-packages' in path.relative_to(stdlib).parts or '__pycache__' in path.parts:
            continue
        if path.is_file() and (path.suffix in ('.py', '.so') or '.so.' in path.name):
            files.add(path.resolve())
    for folder in (numpy_root, numpy_root.parent / 'numpy.libs'):
        if folder.exists():
            files.update(path.resolve() for path in folder.rglob('*') if path.is_file()
                         and (path.suffix in ('.py', '.so') or '.so.' in path.name))
    dependencies = set(); unavailable = {}; loaded = _loaded_files()
    for path in sorted(files):
        if path.suffix == '.py':
            continue
        closure, missing = _ldd(path, allow_missing=True)
        dependencies.update(closure)
        if missing:
            if str(path) in loaded:
                raise ValueError('Loaded Python extension has unresolved dependencies: ' + str(path))
            unavailable[str(path)] = missing
    return files | dependencies, unavailable


def _elf_closure(paths):
    pending = set()
    for path in paths:
        value = _absolute(path); parent, name = value.rsplit('/', 1)
        directory = _directory(parent)
        fd = None
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise ValueError('Regular ELF inspection input required')
            start = os.read(fd, 4)
            if _stable(before) != _stable(os.fstat(fd)) or _stable(before) != _stable(os.stat(name, dir_fd=directory, follow_symlinks=False)):
                raise ValueError('ELF inspection input changed')
            if start == b'\x7fELF':
                pending.add(Path(path).resolve())
        finally:
            if fd is not None:
                os.close(fd)
            os.close(directory)
    checked = set()
    while pending:
        path = min(pending); pending.remove(path)
        if path in checked:
            continue
        checked.add(path)
        dependencies, _ = _ldd(path)
        pending.update(dependencies - checked)
    return checked


def _executable(name):
    invocation = sys.executable if name == 'python' else shutil.which(name)
    if not invocation or not Path(invocation).is_file():
        raise ValueError('Missing independently measured executable: ' + name)
    resolved = Path(invocation).resolve()
    if name == 'python':
        version = sys.version
    elif name == 'git':
        version = _command([str(resolved), '--version']).decode().strip()
    else:
        version = json.loads(_command([str(resolved), '-p', 'JSON.stringify(process.versions)']))
    return {'invocation': str(Path(invocation).absolute()), 'resolved': str(resolved),
            'sha256': pin(resolved)['sha256'], 'version': version}


def expected_runtime():
    """Independent implementation of original local runtime scope, no capture."""
    python_files, unavailable = _python_inventory()
    executables = {name: _executable(name) for name in ('python', 'git', 'node')}
    git_exec_path = Path(_command([executables['git']['resolved'], '--exec-path']).decode().strip()).resolve()
    if not git_exec_path.is_dir():
        raise ValueError('Missing installed Git helper directory')
    git_files = {path.resolve() for path in git_exec_path.rglob('*') if path.is_file()}
    external = git_files | {Path(record['resolved']) for record in executables.values()}
    elf = _elf_closure(external)
    files = sorted(str(path) for path in python_files | external | elf)
    return {'runtime_file_inventory': files,
        'runtime_sha256s': {path: pin(path)['sha256'] for path in files},
        'executables': executables, 'git_exec_path': str(git_exec_path),
        'git_runtime_file_inventory': sorted(str(path) for path in git_files),
        'git_node_elf_inventory': sorted(str(path) for path in elf),
        'unavailable_unused_python_extensions': unavailable,
        'python': sys.version, 'numpy': np.__version__}


def expected_supplement():
    stdlib = Path(sysconfig.get_path('stdlib')); files = set()
    for path in stdlib.rglob('*.pyc'):
        if 'site-packages' not in path.relative_to(stdlib).parts and path.is_file():
            files.add(path.resolve())
    for entry in sys.path:
        path = Path(entry)
        if path.suffix == '.zip' and path.is_file():
            files.add(path.resolve())
    for value in ('/etc/ssl/openssl.cnf', '/usr/lib/ssl/openssl.cnf'):
        path = Path(value)
        if path.is_file():
            files.add(path.resolve())
    for folder in ('/usr/lib/x86_64-linux-gnu/ossl-modules', '/usr/lib/aarch64-linux-gnu/ossl-modules'):
        root = Path(folder)
        if root.exists():
            files.update(path.resolve() for path in root.glob('*.so') if path.is_file())
    return {'schema': fixture.SCHEMA + '-engineering-runtime-supplement',
        'files': {str(path): pin(path) for path in sorted(files)},
        'repository_bytecode_copied': False, 'child_python_flags': ['-I', '-S', '-B'],
        'child_repository_imports_use_fresh_source_only': True,
        'scientific_runtime_qualified': False}


def environment_fingerprints():
    return {name: hashlib.sha256(os.environ[name].encode()).hexdigest()
            if name in os.environ else None for name in freezer.ENVIRONMENT_KEYS}


def _exact(value, expected, label):
    # JSON equality alone treats True == 1. Wire equality retains scalar types.
    if canonical(value) != canonical(expected):
        raise ValueError('Exact independent preparation comparison differs: ' + label)


def validate_complete_freeze(freeze, repo):
    """Original structural validator plus independent full named-scope replay."""
    freezer.validate_freeze(freeze)
    if set(freeze) != FREEZE_KEYS:
        raise ValueError('Exact complete original freezer structure required')
    _exact(freeze['coverage'], COVERAGE, 'original freezer coverage')
    code = repository_inventory(repo)
    _exact(freeze['repository_code_inventory'], code, 'repository code inventory')
    for map_name in ('code_sha256s', 'input_sha256s'):
        for path, digest in freeze[map_name].items():
            actual = pin(Path(repo) / _relative(path), sole_link=True)
            if actual['sha256'] != digest:
                raise ValueError('Frozen repository/input bytes changed: ' + path)
    for path, digest in freeze['runtime_sha256s'].items():
        path = _absolute(path)
        if str(Path(path).resolve()) != path:
            raise ValueError('Runtime inventory path alias refused: ' + path)
        if pin(path)['sha256'] != digest:
            raise ValueError('Frozen external runtime bytes changed: ' + path)
    current = expected_runtime()
    for field in freezer.RUNTIME_FIELDS:
        _exact(freeze[field], current[field], 'original runtime closure field ' + field)
    _exact(freeze['environment_fingerprints'], environment_fingerprints(), 'parent environment fingerprints')
    if _loaded_files() & set(freeze['unavailable_unused_python_extensions']):
        raise ValueError('Unavailable optional Python extension entered audit runtime')
    return current


def audit(plan, complete_freeze=None, *, repo=REPO, materialized_code_root=None, derived_root=None):
    """Validate a prospective snapshot; successful audit still stays blocked."""
    repo = Path(_absolute(repo))
    root_fd = _directory(str(repo)); os.close(root_fd)
    implementation_pins = {path: pin(path, sole_link=True) for path in AUDIT_IMPLEMENTATION_PATHS}
    _exact(implementation_pins, AUDIT_IMPLEMENTATION_PINS, 'audit implementation bytes after import')
    if not isinstance(plan, dict):
        raise ValueError('Prospective compact-control plan required')
    # Check filesystem identities before build_plan can read through an alias.
    code_pins = {path: pin(repo / _relative(path), sole_link=True) for path in fixture.CODE_FILES}
    _exact(plan.get('code_files'), code_pins, 'prospective code pins')
    _exact(plan, fixture.build_plan(repo), 'entire current prospective plan')
    supplement = expected_supplement()
    _exact(plan['engineering_runtime_supplement'], supplement, 'engineering runtime supplement inventory/bytes/flags')
    _exact(plan['child_environment'], {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}, 'fixed child environment')
    derived = fixture.templates((repo / fixture.CODE_FILES[0]).read_text())
    derived_pins = {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                    for name, raw in derived.items()}
    _exact(plan['derived_code'], derived_pins, 'prospective derived code pins')
    materialized = materialized_code_root is not None or derived_root is not None
    if materialized_code_root is None and derived_root is not None or materialized_code_root is not None and derived_root is None:
        raise ValueError('Both materialized code and derived source roots required')
    if materialized:
        code_root = Path(_absolute(materialized_code_root)); source_root = Path(_absolute(derived_root))
        for path, wanted in code_pins.items():
            _exact(pin(code_root / path, sole_link=True), wanted, 'materialized source ' + path)
        for name, wanted in derived_pins.items():
            _exact(pin(source_root / name, sole_link=True), wanted, 'materialized derived source ' + name)
    current = None
    if complete_freeze is not None:
        current = validate_complete_freeze(complete_freeze, repo)
        for path, wanted in code_pins.items():
            identities = complete_freeze['input_sha256s'] if path.startswith('tests/') else complete_freeze['code_sha256s']
            if identities.get(path) != wanted['sha256']:
                raise ValueError('Original complete freeze omitted prospective material/test pin: ' + path)
        for name, record in plan['runtime_executables'].items():
            executable = current['executables'][name]
            _exact(record, {'path': executable['resolved'], **pin(executable['resolved'])}, 'prospective executable ' + name)
    joined = {} if current is None else {path: {'sha256': value, **pin(path)}
                                        for path, value in current['runtime_sha256s'].items()}
    for path, wanted in supplement['files'].items():
        if path in joined:
            _exact(joined[path], wanted, 'overlapping runtime supplement pin ' + path)
        joined[path] = wanted
    return {'schema': SCHEMA, 'namespace': fixture.NAMESPACE,
        'status': 'PREPARATION_COHERENCE_VERIFIED_EXECUTION_BLOCKED',
        'plan_sha256': hashlib.sha256(canonical(plan)).hexdigest(),
        'audit_implementation_code_pins': implementation_pins,
        'audit_implementation_pins_bound_by_freeze': complete_freeze is not None
            and repo == REPO and all(complete_freeze['code_sha256s'].get(str(Path(path).relative_to(REPO)))
                                    == wanted['sha256'] for path, wanted in implementation_pins.items()),
        'original_complete_freeze_supplied': complete_freeze is not None,
        'original_freezer_structural_validation_verified': current is not None,
        'independent_original_local_runtime_scope_verified': current is not None,
        'original_complete_freeze_sha256': hashlib.sha256(canonical(complete_freeze)).hexdigest() if current is not None else None,
        'exact_prospective_code_and_derived_pins_verified': True,
        'materialized_code_and_derived_pins_verified': materialized,
        'exact_supplement_inventory_and_bytes_verified': True,
        'runtime_and_supplement_union_files': len(joined),
        'runtime_and_supplement_union_sha256': hashlib.sha256(canonical(joined)).hexdigest(),
        'parent_environment_allowlist_fingerprints_verified': current is not None,
        'fixed_child_environment_and_python_flags_verified': True,
        'exact_material_child_argv_independently_admitted': False,
        'complete_parent_environment_frozen': False,
        'complete_execution_runtime_closure_qualified': False,
        'public_immutable_preread_verified': False,
        'all_five_execution_blockers_closed': False,
        'remaining_execution_blockers': list(fixture.EXECUTION_BLOCKERS),
        'missing_evidence': ([ 'Exact current complete original runner/broker freeze.' ] if current is None else [])
            + ([ 'Independently audited materialized code and derived source bytes.' ] if not materialized else [])
            + ['Complete parent environment and exact independently admitted child argv joins.',
               'Immutable public-preread proof and independent source-worker admission.',
               'Complete process lifetime, final storage/timing, and prepared/terminal identity joins.'],
        'runtime_scope_limitations': dict(COVERAGE), **AUTHORITY}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--complete-freeze', type=Path)
    parser.add_argument('--repo', type=Path, default=REPO)
    parser.add_argument('--materialized-code-root', type=Path)
    parser.add_argument('--derived-root', type=Path)
    args = parser.parse_args()
    result = audit(read_json(args.plan.absolute()),
        read_json(args.complete_freeze.absolute()) if args.complete_freeze else None,
        repo=args.repo.absolute(),
        materialized_code_root=args.materialized_code_root.absolute() if args.materialized_code_root else None,
        derived_root=args.derived_root.absolute() if args.derived_root else None)
    print(canonical(result).decode())


# Record the local source identities of the auditor and its already imported
# repository dependencies. Recheck those bytes before reporting an audit.
AUDIT_IMPLEMENTATION_PATHS = tuple(sorted({str(Path(__file__).resolve())} | {
    value for value in _loaded_files() if Path(value).is_relative_to(REPO)
    and str(Path(value).relative_to(REPO)).startswith(('scripts/', 'src/seti_repeater/'))
    and Path(value).suffix == '.py'}))
AUDIT_IMPLEMENTATION_PINS = {path: pin(path, sole_link=True) for path in AUDIT_IMPLEMENTATION_PATHS}


if __name__ == '__main__':
    main()
