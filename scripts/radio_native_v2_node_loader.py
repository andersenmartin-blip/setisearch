#!/usr/bin/env python3
"""Pinned local Node source launcher; this component grants no authority.

The parent reads, hashes, and transfers exact repository JavaScript buffers.
The child hashes each buffer before compiling it and implements its own finite
CommonJS resolver.  Package/global modules, JSON imports and native addons are
outside this resolver.  This source policy is for trusted frozen project code;
it is not a hostile-code sandbox or a transport/execution qualification.
"""
import sys

SCHEMA = 'radio-native-v2-node-source-preflight-v1'
SELF = 'scripts/radio_native_v2_node_loader.py'
DEFAULT_MODULES = ('scripts/radio_native_v2_local_transport.js',
                   'scripts/radio_native_v2_local_worker.js')
BUILTINS = ('fs', 'path', 'crypto', 'child_process', 'perf_hooks', 'readline')
MAX_SOURCE_BYTES = 64 * 1024
MAX_ARGUMENT_BYTES = 96 * 1024
MAX_TOTAL_ARGUMENT_BYTES = 2 * 1024 * 1024
DISABLED = ('reservation_authorized', 'rng_authorized', 'execution_authorized',
            'scientific_execution_authorized', 'restart_authorized',
            'transport_integration_qualified')

# This literal is recovered from the exact hash-verified launcher source by the
# parent, rather than trusted from an earlier possibly stale module import.
BOOTSTRAP = r'''
'use strict';
(() => {
  const nativeRequire = require;
  const fs = nativeRequire('node:fs'), path = nativeRequire('node:path'),
    crypto = nativeRequire('node:crypto'), vm = nativeRequire('node:vm'),
    Module = nativeRequire('node:module');
  const argv = process.argv.slice(1), config = JSON.parse(argv[0]);
  const assert = (ok, message) => { if (!ok) throw Error(message); };
  const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
  const disabled = ['reservation_authorized','rng_authorized','execution_authorized',
    'scientific_execution_authorized','restart_authorized','transport_integration_qualified'];
  assert(config.schema === 'radio-native-v2-node-launch-plan-v1', 'Exact Node launch schema required');
  assert(fs.realpathSync(config.root) === config.root, 'Canonical Node source root required');
  const freezeRaw = fs.readFileSync(config.freeze_path);
  assert(sha(freezeRaw) === config.freeze_sha256, 'Node freeze bytes differ');
  const freeze = JSON.parse(freezeRaw.toString('utf8'));
  assert(freeze.mode === 'PROSPECTIVE_ENGINEERING_ONLY' && disabled.every(key => freeze[key] === false),
    'Node source launcher grants no authority');
  assert(sha(fs.readFileSync(path.join(config.root,config.launcher))) === config.launcher_sha256 &&
    freeze.code_sha256s[config.launcher] === config.launcher_sha256, 'Pinned Node launcher differs');
  assert(sha(Buffer.from(config.bootstrap, 'utf8')) === config.bootstrap_sha256,
    'Pinned Node bootstrap differs');
  const node = freeze.executables.node, git = freeze.executables.git;
  assert(fs.realpathSync(process.execPath) === node.resolved &&
    sha(fs.readFileSync(process.execPath)) === node.sha256 &&
    freeze.runtime_sha256s[node.resolved] === node.sha256, 'Pinned Node executable differs');
  const versions = Object.keys(process.versions).sort();
  assert(JSON.stringify(versions) === JSON.stringify(Object.keys(node.version).sort()) &&
    versions.every(key => process.versions[key] === node.version[key]), 'Pinned Node version differs');
  assert(fs.realpathSync(git.invocation) === git.resolved &&
    sha(fs.readFileSync(git.resolved)) === git.sha256 &&
    freeze.runtime_sha256s[git.resolved] === git.sha256, 'Pinned Git executable differs');
  assert(JSON.stringify(Object.keys(process.env).sort()) === JSON.stringify(Object.keys(config.env).sort()) &&
    Object.keys(config.env).every(key => process.env[key] === config.env[key]), 'Node environment differs');
  assert(process.execArgv.length === 2 && process.execArgv[0] === '-e' &&
    process.execArgv[1] === config.bootstrap, 'Node preload/extra executable arguments refused');
  const sources = new Map(), inventory = {}, cache = new Map(), requestedBuiltins = new Set();
  assert(argv.length === config.source_paths.length + 1, 'Exact Node source buffers required');
  for (let i = 0; i < config.source_paths.length; i++) {
    const relative = config.source_paths[i];
    assert(/^scripts\/[A-Za-z0-9_.-]+\.js$/.test(relative), 'Canonical pinned script path required');
    const encoded = argv[i+1];
    assert(/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(encoded),
      'Canonical source base64 required');
    const bytes = Buffer.from(encoded, 'base64');
    assert(bytes.length <= 65536 && bytes.toString('base64') === encoded &&
      sha(bytes) === freeze.code_sha256s[relative], 'Pinned Node source bytes differ: '+relative);
    const filename = path.join(config.root,relative);
    assert(fs.realpathSync(filename) === filename, 'Node source symlink/escape refused');
    assert(!sources.has(relative), 'Duplicate Node source buffer refused');
    sources.set(relative, { bytes,filename,sha256:sha(bytes) });
  }
  const approved = Object.freeze(['fs','path','crypto','child_process','perf_hooks','readline']);
  assert(JSON.stringify(config.builtins) === JSON.stringify(approved), 'Exact finite Node builtin policy required');
  // Load permitted builtins before closing the native CommonJS resolver.
  const builtinValues = new Map(approved.map(name => [name,nativeRequire('node:'+name)]));
  const refuse = () => { throw Error('Unpinned Node module/addon/source path refused'); };
  Module._load = refuse;
  Module._resolveFilename = refuse;
  process.dlopen = refuse;
  process.binding = refuse;
  if ('getBuiltinModule' in process) process.getBuiltinModule = refuse;
  globalThis.require = refuse;
  globalThis.module = undefined;
  globalThis.eval = refuse;
  globalThis.Function = refuse;
  const resolve = (request, parent) => {
    assert(typeof request === 'string', 'String-only pinned Node require required');
    const name = request.startsWith('node:') ? request.slice(5) : request;
    if (builtinValues.has(name)) return { builtin:name };
    assert(request.startsWith('./') || request.startsWith('../'),
      'Only approved Node builtins or pinned relative scripts allowed: '+request);
    assert(!request.includes('\\') && !/[\x00-\x1f\x7f]/.test(request), 'Canonical Node require path required');
    let relative = path.posix.normalize(path.posix.join(path.posix.dirname(parent),request));
    if (!path.posix.extname(relative)) relative += '.js';
    assert(sources.has(relative), 'Node import absent from exact frozen source buffers: '+relative);
    return { relative };
  };
  const load = relative => {
    assert(sources.has(relative), 'Node entrypoint absent from frozen source buffers: '+relative);
    if (cache.has(relative)) return cache.get(relative).exports;
    const source = sources.get(relative), module = { exports:{},filename:source.filename };
    cache.set(relative,module);
    const localRequire = request => {
      const target = resolve(request,relative);
      if (target.builtin) { requestedBuiltins.add(target.builtin);return builtinValues.get(target.builtin); }
      return load(target.relative);
    };
    localRequire.resolve = request => {
      const target = resolve(request,relative);
      return target.builtin ? 'node:'+target.builtin : sources.get(target.relative).filename;
    };
    Object.freeze(localRequire);
    const text = new TextDecoder('utf-8',{fatal:true}).decode(source.bytes);
    // source.bytes is the exact prehashed buffer; no source-file reread occurs.
    const wrapper = vm.runInThisContext('(function(exports,require,module,__filename,__dirname){\n'+text+'\n})',
      { filename:source.filename,displayErrors:true });
    inventory[relative] = { path:source.filename,sha256:source.sha256,kind:'PREHASHED_EXACT_SOURCE_BUFFER' };
    try { wrapper(module.exports,localRequire,module,source.filename,path.dirname(source.filename)); }
    catch (error) { cache.delete(relative);throw error; }
    return module.exports;
  };
  for (const relative of config.modules) load(relative);
  const record = () => ({ schema:'radio-native-v2-node-source-preflight-v1',mode:'LOCAL_NODE_SOURCE_COMPONENT_ONLY',
    freeze_sha256:config.freeze_sha256,launcher_sha256:config.launcher_sha256,
    bootstrap_sha256:config.bootstrap_sha256,node_executable_sha256:node.sha256,
    git_executable_sha256:git.sha256,node_versions:{...process.versions},
    environment_isolated:true,stdin_consumed_by_bootstrap:false,source_buffers_hashed_before_compile:true,
    arbitrary_commonjs_resolution_disabled:true,external_packages_disabled:true,native_addons_disabled:true,
    public_freeze_verified:false,hostile_code_sandbox:false,qualified_transport_execution:false,
    builtin_whitelist:approved,requested_builtins:Array.from(requestedBuiltins).sort(),
    source_inventory:Object.fromEntries(Object.entries(inventory).map(([name,item])=>[name,{...item}])),
    available_source_buffer_inventory:Object.fromEntries(Array.from(sources,([name,item])=>
      [name,{path:item.filename,sha256:item.sha256,kind:'PREHASHED_AVAILABLE_SOURCE_BUFFER'}])),
    verified_runtime_files:config.verified_runtime_files,
    ...Object.fromEntries(disabled.map(key => [key,false])) });
  if (config.entrypoint === null) process.stdout.write(JSON.stringify(record())+'\n');
  else {
    const entry = load(config.entrypoint.module);
    const deepFreeze = value => {
      if (value && typeof value === 'object') {
        for (const child of Object.values(value)) deepFreeze(child);
        Object.freeze(value);
      } return value;
    };
    Object.defineProperty(globalThis,'__radioNativeV2SourcePolicy',
      { get:() => deepFreeze(record()),configurable:false,enumerable:false });
    assert(typeof entry[config.entrypoint.export] === 'function', 'Pinned Node entry export required');
    const value = entry[config.entrypoint.export](config.entrypoint.options);
    Promise.resolve(value).catch(error => { process.stderr.write(String(error.stack || error)+'\n');process.exitCode=1; });
  }
})();
'''


def _digest_file(path):
    import hashlib
    from pathlib import Path
    result = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def _strict_json(raw):
    import json

    def mapping(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate Node freeze key refused')
            result[key] = value
        return result

    return json.loads(raw, object_pairs_hook=mapping,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON refused')))


def _path(value):
    from pathlib import PurePosixPath
    import re
    if (not isinstance(value, str) or not re.fullmatch(r'scripts/[A-Za-z0-9_.-]+\.js', value)
            or PurePosixPath(value).is_absolute()):
        raise ValueError('Canonical pinned JavaScript script path required')
    return value


def prepare_launch(root, freeze_path, expected_sha256, *, modules=DEFAULT_MODULES,
                   entrypoint=None, source_paths=None):
    """Produce an absolute pinned argv/env plan without consuming child stdin.

    ``entrypoint`` may be {module, export, options}; calling that trusted frozen
    export remains a component action and confers none of the disabled rights.
    The caller must independently retain public freeze/reservation evidence.
    """
    import ast
    import base64
    import hashlib
    import json
    from pathlib import Path
    root = Path(root).resolve()
    freeze_path = Path(freeze_path).resolve()
    raw = freeze_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Node freeze bytes differ')
    freeze = _strict_json(raw)
    if (freeze.get('mode') != 'PROSPECTIVE_ENGINEERING_ONLY'
            or any(freeze.get(key) is not False for key in DISABLED)):
        raise ValueError('Node source launcher grants no authority')
    code = freeze['code_sha256s']
    launcher = root / SELF
    if launcher.resolve() != launcher or not launcher.is_file():
        raise ValueError('Pinned Node launcher symlink/escape refused')
    launcher_bytes = launcher.read_bytes()
    launcher_sha = hashlib.sha256(launcher_bytes).hexdigest()
    if launcher_sha != code.get(SELF):
        raise ValueError('Pinned Node launcher source differs')
    literals = [node.value for node in ast.parse(launcher_bytes).body
                if isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'BOOTSTRAP']
    if len(literals) != 1:
        raise ValueError('Exact pinned Node bootstrap literal required')
    bootstrap = ast.literal_eval(literals[0])
    if not isinstance(bootstrap, str):
        raise ValueError('Exact pinned Node bootstrap source required')
    runtime = freeze['runtime_sha256s']
    for path, digest in runtime.items():
        local = Path(path)
        if (not local.is_absolute() or local.resolve() != local or not local.is_file()
                or _digest_file(local) != digest):
            raise ValueError('Frozen Node runtime dependency differs: '+str(path))
    for name in ('node', 'git'):
        item = freeze['executables'][name]
        invocation, resolved = Path(item['invocation']), Path(item['resolved'])
        if (not invocation.is_absolute() or invocation.resolve() != resolved
                or resolved.resolve() != resolved or runtime.get(str(resolved)) != item['sha256']
                or _digest_file(resolved) != item['sha256']):
            raise ValueError('Pinned Node/Git executable differs: '+name)
    modules = tuple(_path(path) for path in modules)
    if len(set(modules)) != len(modules):
        raise ValueError('Duplicate Node entry modules refused')
    if entrypoint is not None:
        if (not isinstance(entrypoint, dict) or set(entrypoint) != {'module', 'export', 'options'}
                or not isinstance(entrypoint['export'], str)
                or not entrypoint['export'].isidentifier()
                or not isinstance(entrypoint['options'], dict)):
            raise ValueError('Exact Node entrypoint export/options required')
        entrypoint = _strict_json(json.dumps(entrypoint, allow_nan=False))
        _path(entrypoint['module'])
    if source_paths is None:
        source_paths = sorted(path for path in code
                              if path.startswith('scripts/radio_native_v2_') and path.endswith('.js'))
    source_paths = tuple(_path(path) for path in source_paths)
    if len(set(source_paths)) != len(source_paths):
        raise ValueError('Duplicate pinned Node source paths refused')
    needed = set(modules)
    if entrypoint:
        needed.add(entrypoint['module'])
    if not needed.issubset(source_paths):
        raise ValueError('Node module absent from supplied pinned source paths')
    encoded = []
    for relative in source_paths:
        path = root / relative
        if path.resolve() != path or not path.is_file():
            raise ValueError('Pinned Node source symlink/escape refused')
        source = path.read_bytes()
        if len(source) > MAX_SOURCE_BYTES:
            raise ValueError('Pinned Node source exceeds exact buffer cap')
        if hashlib.sha256(source).hexdigest() != code.get(relative):
            raise ValueError('Pinned Node source bytes differ: '+relative)
        source.decode('utf-8', errors='strict')
        encoded.append(base64.b64encode(source).decode('ascii'))
    environment = {'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC'}
    config = {'schema': 'radio-native-v2-node-launch-plan-v1', 'root': str(root),
              'freeze_path': str(freeze_path), 'freeze_sha256': expected_sha256,
              'launcher': SELF, 'launcher_sha256': launcher_sha,
              'bootstrap': bootstrap, 'bootstrap_sha256': hashlib.sha256(bootstrap.encode()).hexdigest(),
              'env': environment, 'source_paths': list(source_paths),
              'builtins': list(BUILTINS), 'modules': list(modules), 'entrypoint': entrypoint,
              'verified_runtime_files': len(runtime)}
    arguments = [freeze['executables']['node']['invocation'], '-e', bootstrap,
                 json.dumps(config, sort_keys=True, separators=(',', ':'), ensure_ascii=True), *encoded]
    if any(len(item.encode()) > MAX_ARGUMENT_BYTES for item in arguments):
        raise ValueError('Node argument exceeds pinned launch cap')
    if sum(len(item.encode())+1 for item in arguments) > MAX_TOTAL_ARGUMENT_BYTES:
        raise ValueError('Node total arguments exceed pinned launch cap')
    return {'arguments': arguments, 'environment': environment, 'cwd': str(root),
            'freeze_sha256': expected_sha256, 'launcher_sha256': launcher_sha,
            'bootstrap_sha256': config['bootstrap_sha256'], 'source_paths': list(source_paths),
            'verified_runtime_files': len(runtime), **{key: False for key in DISABLED}}


def launch_preflight(root, freeze_path, expected_sha256, *, modules=DEFAULT_MODULES,
                     source_paths=None, timeout=120):
    """Import trusted frozen modules in a real subprocess and return its record."""
    import json
    import subprocess
    plan = prepare_launch(root, freeze_path, expected_sha256, modules=modules,
                          source_paths=source_paths)
    completed = subprocess.run(plan['arguments'], cwd=plan['cwd'], env=plan['environment'],
                               stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
    if completed.returncode or completed.stderr:
        raise ValueError('Pinned Node source preflight failed: '
                         + completed.stderr.decode('utf-8', errors='replace')[-4000:])
    proof = json.loads(completed.stdout)
    if (proof.get('schema') != SCHEMA or proof.get('freeze_sha256') != expected_sha256
            or proof.get('launcher_sha256') != plan['launcher_sha256']
            or proof.get('bootstrap_sha256') != plan['bootstrap_sha256']
            or proof.get('public_freeze_verified') is not False
            or any(proof.get(key) is not False for key in DISABLED)):
        raise ValueError('Pinned Node preflight binding differs')
    return proof


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--freeze-path', required=True)
    parser.add_argument('--freeze-sha256', required=True)
    parser.add_argument('--module', action='append')
    options = parser.parse_args()
    print(json.dumps(launch_preflight(options.root, options.freeze_path, options.freeze_sha256,
                                     modules=tuple(options.module) if options.module else DEFAULT_MODULES),
                     sort_keys=True, separators=(',', ':'), ensure_ascii=True))
