#!/usr/bin/env python3
"""Isolated, source-only local import preflight; never an execution authority.

The launcher checks the entrypoint, Python executable and the three CPython
startup encoding sources before starting ``-I -S -B`` with a fresh empty private
cache prefix.  The child then checks every later source before compiling its
bytes.  Existing CPython cache files,
site hooks, namespace packages and origins absent from the freeze are refused.
This is a local source-loader component, not a public freeze/reservation proof.
"""
import sys


SCHEMA = 'radio-native-v2-source-loader-preflight-v1'
SELF = 'scripts/radio_native_v2_source_loader.py'
DEFAULT_MODULES = ('seti_repeater.native_v2_runner_radio',)
STARTUP_SOURCES = ('encodings', 'encodings.aliases', 'encodings.utf_8')
DISABLED = ('reservation_authorized', 'rng_authorized', 'execution_authorized',
            'scientific_execution_authorized', 'restart_authorized',
            'transport_integration_qualified')


def _child_json(raw, scanstring):
    """Parse freeze JSON without importing a source module before pins exist.

    scanstring is required to be part of the pinned CPython executable.  The
    structural parser rejects duplicate keys and nonfinite/invalid numbers.
    """
    text = raw.decode('utf-8')
    position = 0

    def whitespace():
        nonlocal position
        while position < len(text) and text[position] in ' \r\n\t':
            position += 1

    def value():
        nonlocal position
        whitespace()
        if position >= len(text):
            raise ValueError('Incomplete freeze JSON')
        char = text[position]
        if char == '"':
            result, position = scanstring(text, position + 1, True)
            return result
        if char in '[{':
            position += 1
            mapping = char == '{'
            end = '}' if mapping else ']'
            result = {} if mapping else []
            whitespace()
            if position < len(text) and text[position] == end:
                position += 1
                return result
            while True:
                first = value()
                if mapping:
                    if not isinstance(first, str) or first in result:
                        raise ValueError('String/nonduplicate freeze JSON keys required')
                    whitespace()
                    if position >= len(text) or text[position] != ':':
                        raise ValueError('Freeze JSON separator missing')
                    position += 1
                    result[first] = value()
                else:
                    result.append(first)
                whitespace()
                if position >= len(text):
                    raise ValueError('Incomplete freeze JSON container')
                char = text[position]
                position += 1
                if char == end:
                    return result
                if char != ',':
                    raise ValueError('Freeze JSON delimiter missing')
        for spelling, result in (('true', True), ('false', False), ('null', None)):
            if text.startswith(spelling, position):
                position += len(spelling)
                return result
        start = position
        if char == '-':
            position += 1
        digits = position
        while position < len(text) and text[position] in '0123456789':
            position += 1
        if position == digits or (position - digits > 1 and text[digits] == '0'):
            raise ValueError('Invalid freeze JSON number')
        # The prospective file freeze uses integral counts; floating-point
        # metadata is deliberately outside this tiny bootstrap parser.
        return int(text[start:position])

    result = value()
    whitespace()
    if position != len(text):
        raise ValueError('Trailing/unsupported freeze JSON bytes')
    return result


def _child(root, freeze_path, expected_sha256, modules):
    # Only built-in or frozen imports are permitted until pins are parsed.
    if (not sys.flags.isolated or not sys.flags.no_site
            or not sys.flags.dont_write_bytecode or not sys.flags.ignore_environment):
        raise ValueError('Source loader requires Python -I -S -B')
    if any(name not in sys.builtin_module_names for name in ('_hashlib', '_json')):
        raise ValueError('Source-loader bootstrap requires pinned built-in _hashlib and _json')
    import os
    import _hashlib
    import _json
    import _io
    import _frozen_importlib as bootstrap
    import _frozen_importlib_external as external
    startup = {}
    for name in tuple(sys.modules):
        module = sys.modules[name]
        spec = getattr(module, '__spec__', None)
        if name == '__main__':
            continue
        if name in STARTUP_SOURCES and spec is not None and spec.origin.endswith('.py'):
            startup[name] = (spec.origin, spec.cached)
            continue
        if spec is None or spec.origin not in ('built-in', 'frozen'):
            raise ValueError('Unverified source entered bootstrap: ' + name)
    sha256 = _hashlib.openssl_sha256

    def read(path):
        with _io.open(path, 'rb') as source:
            return source.read()

    def file_sha(path):
        result = sha256()
        with _io.open(path, 'rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                result.update(chunk)
        return result.hexdigest()

    root = os.path.realpath(root)
    raw = read(freeze_path)
    if sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Source-loader freeze bytes differ')
    freeze = _child_json(raw, _json.scanstring)
    if (freeze.get('mode') != 'PROSPECTIVE_ENGINEERING_ONLY'
            or any(freeze.get(key) is not False for key in DISABLED)):
        raise ValueError('Source loader grants no authority')
    runtime = freeze['runtime_sha256s']
    code = freeze['code_sha256s']
    python = freeze['executables']['python']
    if (os.path.realpath(sys.executable) != python['resolved']
            or sys.version != python['version']
            or file_sha(sys.executable) != python['sha256']
            or runtime.get(python['resolved']) != python['sha256']):
        raise ValueError('Pinned Python executable/version differs')
    entry = os.path.join(root, SELF)
    if (os.path.realpath(__file__) != entry or file_sha(entry) != code.get(SELF)
            or globals().get('_ENTRY_EXECUTED_SHA256') != code.get(SELF)):
        raise ValueError('Pinned source-loader entrypoint differs')
    cache_prefix = sys.pycache_prefix
    if (not isinstance(cache_prefix, str) or not os.path.isabs(cache_prefix)
            or os.path.realpath(cache_prefix) != cache_prefix
            or not os.path.isdir(cache_prefix) or os.listdir(cache_prefix)
            or set(startup) != set(STARTUP_SOURCES)):
        raise ValueError('Fresh empty startup cache prefix required')
    startup_records = {}
    for name, (path, cached) in startup.items():
        if (os.path.realpath(path) != path or runtime.get(path) != file_sha(path)
                or not isinstance(cached, str)
                or os.path.commonpath((cached, cache_prefix)) != cache_prefix
                or os.path.exists(cached)):
            raise ValueError('Pinned CPython startup source/cache differs: ' + name)
        startup_records[name] = {'path': path, 'sha256': runtime[path],
                                 'kind': 'PRELAUNCH_VERIFIED_CPYTHON_STARTUP_SOURCE'}
    expected_env = _environment(freeze, os.path)
    if dict(os.environ) != expected_env:
        raise ValueError('Source-loader child environment differs')
    pins = dict(runtime)
    for path, digest in code.items():
        if (not isinstance(path, str) or path.startswith('/') or '\\' in path
                or any(part in ('', '.', '..') for part in path.split('/'))):
            raise ValueError('Canonical code path required')
        resolved = os.path.realpath(os.path.join(root, path))
        if resolved != os.path.join(root, path):
            raise ValueError('Code symlinks/source escapes refused')
        if resolved in pins and pins[resolved] != digest:
            raise ValueError('Conflicting source-loader pins')
        pins[resolved] = digest
    for path, digest in pins.items():
        if (not isinstance(path, str) or not os.path.isabs(path)
                or os.path.realpath(path) != path or file_sha(path) != digest):
            raise ValueError('Frozen local dependency differs: ' + str(path))
    roots = [os.path.join(root, 'src'), os.path.join(root, 'scripts')]
    stdlib = os.path.join(sys.base_prefix, 'lib',
                         'python' + str(sys.version_info.major) + '.' + str(sys.version_info.minor))
    roots.extend((stdlib, os.path.join(stdlib, 'lib-dynload')))
    numpy_roots = {os.path.dirname(os.path.dirname(path)) for path in runtime
                   if path.endswith('/numpy/__init__.py')}
    if len(numpy_roots) > 1:
        raise ValueError('Multiple NumPy roots refused')
    roots.extend(sorted(numpy_roots))
    roots = tuple(path for path in roots if os.path.isdir(path))
    records = {}

    class DirectSource:
        def __init__(self, fullname, origin, data):
            self.fullname, self.path, self.data = fullname, origin, data

        def create_module(self, spec):
            return None

        def exec_module(self, module):
            # The bytes hashed by the finder are the exact bytes compiled; no
            # second file read and no timestamp/hash .pyc validation occurs.
            compiled = compile(self.data, self.path, 'exec', dont_inherit=True)
            exec(compiled, module.__dict__)

        def get_filename(self, fullname):
            return self.path

        def get_source(self, fullname):
            return self.data.decode('utf-8')

        def get_data(self, path):
            resolved = os.path.realpath(path)
            data = read(resolved)
            if pins.get(resolved) != sha256(data).hexdigest():
                raise ValueError('Unpinned loader data requested: ' + resolved)
            return data

    class FrozenFinder:
        @staticmethod
        def find_spec(fullname, path=None, target=None):
            spec = bootstrap.BuiltinImporter.find_spec(fullname)
            if spec is None:
                spec = bootstrap.FrozenImporter.find_spec(fullname)
            if spec is not None:
                return spec
            search = roots if path is None else tuple(path)
            if any(not any(os.path.commonpath((os.path.realpath(p), r)) == r
                           for r in roots) for p in search):
                raise ValueError('Unpinned import search path: ' + fullname)
            spec = external.PathFinder.find_spec(fullname, search, target)
            if spec is None:
                return None
            if spec.origin is None:
                raise ValueError('Namespace-package source authority refused: ' + fullname)
            origin = os.path.realpath(spec.origin)
            if origin != spec.origin or origin not in pins:
                raise ValueError('Import origin absent from freeze: ' + fullname)
            data = read(origin)
            actual = sha256(data).hexdigest()
            if actual != pins[origin]:
                raise ValueError('Frozen import bytes differ: ' + fullname)
            if origin.endswith('.py'):
                spec.loader = DirectSource(fullname, origin, data)
                kind = 'DIRECT_SOURCE_BYTES'
            elif any(origin.endswith(suffix) for suffix in external.EXTENSION_SUFFIXES):
                if not isinstance(spec.loader, external.ExtensionFileLoader):
                    raise ValueError('Pinned extension loader differs: ' + fullname)
                kind = 'PINNED_EXTENSION'
            else:
                raise ValueError('Bytecode/non-source module refused: ' + fullname)
            records[fullname] = {'path': origin, 'sha256': actual, 'kind': kind}
            return spec

    finder = FrozenFinder()
    sys.path[:] = roots
    sys.meta_path[:] = [finder]
    sys.path_importer_cache.clear()
    for name in modules:
        if (not isinstance(name, str) or not name
                or any(not part.isidentifier() for part in name.split('.'))):
            raise ValueError('Exact import module name required')
        __import__(name)
    if sys.meta_path != [finder] or tuple(sys.path) != roots:
        raise ValueError('Imported source changed pinned finder/path policy')
    source_records = {}
    executable_records = {}
    derived_records = {}
    for name, module in tuple(sys.modules.items()):
        if name == '__main__':
            continue
        spec = getattr(module, '__spec__', None)
        if spec is None:
            # Python 3.12 typing inserts two class namespace aliases into
            # sys.modules.  They carry no executable module/file spec.  Admit
            # only these exact objects created by the already-verified source.
            if (name in ('typing.io', 'typing.re') and 'typing' in records
                    and module is getattr(sys.modules['typing'], name.split('.')[1], None)
                    and getattr(module, '__module__', None) == 'typing'):
                derived_records[name] = {'defining_module': 'typing',
                                         'source_sha256': records['typing']['sha256']}
                continue
            raise ValueError('Loaded module has no pinned import origin: ' + name)
        if spec.origin in ('built-in', 'frozen'):
            executable_records[name] = spec.origin
        elif name in startup_records and spec.origin == startup_records[name]['path']:
            source_records[name] = startup_records[name]
        elif name not in records or os.path.realpath(spec.origin) != records[name]['path']:
            raise ValueError('Loaded module bypassed frozen finder: ' + name)
        else:
            source_records[name] = records[name]
    import json
    if sys.meta_path != [finder] or tuple(sys.path) != roots:
        raise ValueError('Proof serialization changed source-loader policy')
    # JSON's own imports are included after it has passed through the finder.
    source_records = {**startup_records, **{name: records[name] for name in sorted(records)}}
    proof = {'schema': SCHEMA, 'mode': 'LOCAL_IMPORT_PREFLIGHT_ONLY',
             'freeze_sha256': expected_sha256, 'python_executable_sha256': python['sha256'],
             'entrypoint_sha256': code[SELF], 'modules': list(modules),
             'source_only_imports_verified': True, 'site_hooks_disabled': True,
             'environment_isolated': True, 'bytecode_cache_read': False,
             'bytecode_cache_write': False, 'public_freeze_verified': False,
             'bootstrap_origin': 'PINNED_PYTHON_PLUS_THREE_PRELAUNCH_VERIFIED_STARTUP_SOURCES',
             'startup_cache_prefix_fresh_and_empty': True,
             'source_inventory': source_records, 'builtin_frozen_inventory': executable_records,
             'derived_module_alias_inventory': derived_records,
             'restricted_search_roots': list(roots), 'verified_files': len(pins),
             **{key: False for key in DISABLED}}
    print(json.dumps(proof, sort_keys=True, separators=(',', ':'), ensure_ascii=True))


def _environment(freeze, path_module):
    executable_dirs = sorted({path_module.dirname(freeze['executables'][name]['invocation'])
                              for name in ('git', 'node')})
    return {'PATH': path_module.pathsep.join(executable_dirs), 'LANG': 'C.UTF-8',
            'LC_ALL': 'C.UTF-8', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}


def launch_preflight(root, freeze_path, expected_sha256, *, modules=DEFAULT_MODULES,
                     timeout=120):
    """Hash-check a prospective local freeze and run its source-only child.

    The caller must separately establish immutable public readback.  This API
    deliberately produces no freeze verifier accepted by the native runner.
    """
    import hashlib
    import json
    import os
    from pathlib import Path
    import subprocess
    import tempfile
    root = Path(root).resolve()
    freeze_path = Path(freeze_path).resolve()
    raw = freeze_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Source-loader freeze bytes differ')
    freeze = json.loads(raw)
    if any(freeze.get(key) is not False for key in DISABLED):
        raise ValueError('Source loader grants no authority')
    python = freeze['executables']['python']
    entry = root / SELF
    if (hashlib.sha256(entry.read_bytes()).hexdigest() != freeze['code_sha256s'].get(SELF)
            or hashlib.sha256(Path(python['resolved']).read_bytes()).hexdigest() != python['sha256']
            or Path(python['invocation']).resolve() != Path(python['resolved'])):
        raise ValueError('Pinned launch executable/entrypoint differs')
    # CPython loads these before user code can install an import finder.  A
    # fresh cache prefix makes startup compile the pinned sources rather than
    # consult existing adjacent/cache-prefix bytecode.  The child checks again.
    stdlib = Path(python['resolved']).parents[1] / 'lib' / ('python' + str(sys.version_info.major)
                                                         + '.' + str(sys.version_info.minor))
    for name in STARTUP_SOURCES:
        path = stdlib / (name.replace('.', '/') + ('.py' if '.' in name else '/__init__.py'))
        if (str(path.resolve()) != str(path)
                or hashlib.sha256(path.read_bytes()).hexdigest() != freeze['runtime_sha256s'].get(str(path))):
            raise ValueError('Pinned CPython startup source differs: ' + name)
    # Feed the already-verified exact buffer to compile: executing a path and
    # hashing it later could authenticate different bytes after a replacement.
    entry_source = entry.read_bytes()
    if hashlib.sha256(entry_source).hexdigest() != freeze['code_sha256s'].get(SELF):
        raise ValueError('Pinned entrypoint changed before launch')
    bootstrap_code = ('import sys\n'
                      'if "_hashlib" not in sys.builtin_module_names: '
                      'raise ValueError("Pinned builtin hash bootstrap required")\n'
                      'import _hashlib\n'
                      '_entry_source=sys.stdin.buffer.read()\n'
                      '_ENTRY_EXECUTED_SHA256=_hashlib.openssl_sha256(_entry_source).hexdigest()\n'
                      '__file__=sys.argv[1]\n'
                      'sys.argv[:]=sys.argv[1:]\n'
                      'exec(compile(_entry_source,__file__,"exec"),globals())\n')
    with tempfile.TemporaryDirectory(prefix='radio-source-only-cache-') as cache_prefix:
        arguments = [python['invocation'], '-I', '-S', '-B', '-X', 'pycache_prefix=' + cache_prefix,
                     '-c', bootstrap_code, str(entry), '--child',
                     str(root), str(freeze_path), expected_sha256, *modules]
        completed = subprocess.run(arguments, cwd=root, env=_environment(freeze, os.path),
                                   input=entry_source, capture_output=True, timeout=timeout)
        if list(Path(cache_prefix).rglob('*')):
            raise ValueError('Source-loader wrote/read unexpected startup cache files')
    if completed.returncode:
        raise ValueError('Isolated source-loader preflight failed: '
                         + completed.stderr.decode('utf-8', errors='replace')[-4000:])
    if completed.stderr:
        raise ValueError('Unexpected source-loader stderr')
    proof = json.loads(completed.stdout)
    if (proof.get('schema') != SCHEMA or proof.get('freeze_sha256') != expected_sha256
            or proof.get('modules') != list(modules)
            or proof.get('public_freeze_verified') is not False
            or any(proof.get(key) is not False for key in DISABLED)):
        raise ValueError('Source-loader proof binding differs')
    return proof


if __name__ == '__main__':
    if len(sys.argv) >= 6 and sys.argv[1] == '--child':
        _child(sys.argv[2], sys.argv[3], sys.argv[4], tuple(sys.argv[5:]))
    else:
        import argparse
        import json
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--root', required=True)
        parser.add_argument('--freeze-path', required=True)
        parser.add_argument('--freeze-sha256', required=True)
        parser.add_argument('--module', action='append')
        args = parser.parse_args()
        print(json.dumps(launch_preflight(args.root, args.freeze_path, args.freeze_sha256,
                                         modules=tuple(args.module or DEFAULT_MODULES)),
                         sort_keys=True, indent=2))
