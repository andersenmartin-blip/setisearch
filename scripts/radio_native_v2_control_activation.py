#!/usr/bin/env python3
"""Fail-closed marker-only activation proof for one engineering control.

This module validates Git/object and byte identities only. It does not import or
run the material fixture, create a scope, generate an input, reserve a case, use
RNG, read telescope data, or grant native/scientific authority.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import types

SCHEMA = 'radio-native-v2-control-single-activation-v2'
RECEIPT_SCHEMA = 'radio-native-v2-control-single-activation-receipt-v2'
READBACK_SCHEMA = 'radio-native-v2-control-single-activation-public-readback-v1'
NAMESPACE = 'radio-native-v2-control-activation-transition-20261002b'
REPOSITORY = 'andersenmartin-blip/setisearch'
BRANCH = 'm43-support-qualification'
MARKER = 'config/radio_native_v2_control_activation_20261002b.activate.json'
SPENT_MARKER = 'config/radio_native_v2_control_activation_20261002a.activate.json'
SPENT_ACTIVATION_COMMIT = 'ba1b6c918931a02a84cd23e0e14057bd9f700e40'
CUSTODY_SOURCE = 'scripts/radio_native_v2_runtime_custody.py'
CUSTODY_IMPLEMENTATION_PIN = {'bytes':22519,
    'sha256':'d0cd311c1615a2c299b101ca75b98ba2412b41bb1cfd668725461e4d307fb0b5'}
ACTIVATION_GIT_IMPLEMENTATION_PIN = {'path':'/usr/local/bin/git','bytes':19135768,
    'sha256':'2dae8066ef4d6a926561b4b0eaca7b458d4f5b56bb83760656e6baa7fc3e974f'}
DISABLED = ('reservation_authorized', 'rng_authorized',
    'scientific_execution_authorized', 'native_execution_authorized',
    'restart_authorized', 'automatic_retry')
HASH = re.compile(r'[0-9a-f]{64}\Z')
COMMIT = re.compile(r'[0-9a-f]{40}\Z')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode()


class _ActivationGitScope:
    def __init__(self, root, executable):
        self.root = str(root); self.executable = executable; self.closed = False

    def close(self):
        self.closed = True


def _git(root, *arguments, activation_scope=None):
    if (not isinstance(activation_scope, _ActivationGitScope)
            or activation_scope.closed or activation_scope.root != str(root)):
        raise ValueError('Git is permitted only inside the checked activation-only phase')
    environment = {key: value for key, value in os.environ.items()
        if not key.startswith('GIT_')}
    environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
        GIT_CONFIG_SYSTEM='/dev/null', GIT_NO_REPLACE_OBJECTS='1',
        GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    return subprocess.check_output([activation_scope.executable, '--no-replace-objects', *arguments],
        cwd=root, env=environment, text=True, timeout=20).strip()


def _relative(value):
    if (type(value) is not str or not value or PurePosixPath(value).is_absolute()
            or '\\' in value or any(part in ('', '.', '..') for part in value.split('/'))
            or re.search(r'[\x00-\x1f\x7f]', value)):
        raise ValueError('Canonical relative activation path required')
    return value


def _sha(value, label):
    if type(value) is not str or not HASH.fullmatch(value):
        raise ValueError('Exact lowercase SHA256 required: '+label)
    return value


def _commit(value, label):
    if type(value) is not str or not COMMIT.fullmatch(value):
        raise ValueError('Exact lowercase commit required: '+label)
    return value


def _absolute(value):
    value = os.fspath(value)
    if (type(value) is not str or not value.startswith('/') or value == '/'
            or '\\' in value or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value[1:].split('/'))):
        raise ValueError('Canonical absolute control scope required')
    return value


def _read_regular(path, maximum):
    path = Path(path)
    if not path.is_absolute(): path = path.absolute()
    _absolute(str(path))
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in path.parts[1:-1]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory); directory = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= maximum:
                raise ValueError('Bounded sole-link regular activation evidence required')
            chunks = []; remaining = before.st_size+1
            while remaining:
                raw = os.read(fd, min(65536, remaining))
                if not raw: break
                chunks.append(raw); remaining -= len(raw)
            raw = b''.join(chunks); after = os.fstat(fd)
            named = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
            identity = lambda info:(info.st_dev,info.st_ino,info.st_mode,info.st_nlink,
                info.st_size,info.st_mtime_ns,info.st_ctime_ns)
            if len(raw) != before.st_size or identity(before) != identity(after) or identity(after) != identity(named):
                raise ValueError('Activation evidence changed during descriptor read')
            return raw
        finally: os.close(fd)
    finally: os.close(directory)


def _custody_module(root):
    path = Path(root)/CUSTODY_SOURCE
    raw = _read_regular(path, 2*1024*1024)
    if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} != CUSTODY_IMPLEMENTATION_PIN:
        raise ValueError('Custody source differs from independent activation implementation pin')
    module = types.ModuleType('pinned_activation_runtime_custody'); module.__file__ = str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module


def _custody_contract(freeze, custody):
    manifest = freeze.get('runtime_custody_manifest')
    digest = _sha(freeze.get('runtime_custody_manifest_sha256'),'runtime custody manifest')
    if hashlib.sha256(canonical(manifest)).hexdigest() != digest:
        raise ValueError('Frozen runtime custody manifest canonical hash differs')
    material = {freeze['executables'][name]['resolved'] for name in ('python','node')}
    material.update(path for path in freeze['runtime_file_inventory'] if re.search(r'\.so(?:\.|$)',Path(path).name))
    activation_paths = sorted({freeze['executables']['git']['resolved'], *freeze['git_runtime_file_inventory']} - material)
    arguments = {'runtime_paths':freeze['runtime_file_inventory'],
        'runtime_sha256s':freeze['runtime_sha256s'], 'activation_only_paths':activation_paths,
        'alias_roots':sorted({str(Path(freeze['executables']['git']['resolved']).parent),freeze['git_exec_path']})}
    custody.validate_manifest_structure(manifest, **arguments)
    return manifest, digest, arguments


def _activation_git_contract(freeze,manifest):
    expected = ACTIVATION_GIT_IMPLEMENTATION_PIN
    record = freeze['executables']['git']
    if record['resolved'] != expected['path'] or record['sha256'] != expected['sha256']:
        raise ValueError('Activation Git differs from independently reviewed executable pin')
    actual = manifest['runtime_files'].get(expected['path'])
    if (type(actual) is not dict or actual.get('bytes') != expected['bytes']
            or actual.get('sha256') != expected['sha256']):
        raise ValueError('Frozen activation Git custody differs from independent executable pin')


def _read_json(path, maximum=16*1024*1024):
    try: raw = _read_regular(path,maximum)
    except OSError as failure:
        raise ValueError('Activation evidence is not a readable stable regular file') from failure
    value = json.loads(raw, object_pairs_hook=_unique)
    if type(value) is not dict: raise ValueError('Activation JSON object required')
    if canonical(value)+b'\n' != raw:
        raise ValueError('Canonical newline-terminated activation JSON required')
    return value, raw


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate activation JSON property refused')
        value[key] = item
    return value


def _pin_value(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def verify_marker_checkout(root, *, plan_path, freeze_path, preread_path,
        activation_readback_path, execution_scope, marker_path=MARKER):
    """Verify one public marker-only child and return a bounded worker receipt."""
    root = Path(_absolute(str(Path(root).absolute()))); marker_path = _relative(marker_path)
    if marker_path == SPENT_MARKER:
        raise ValueError('The failed historical activation marker is permanently spent')
    if marker_path != MARKER: raise ValueError('Exact prospective unique activation marker path required')
    execution_scope = _absolute(execution_scope)
    plan_path = _relative(plan_path); freeze_path = _relative(freeze_path)
    preread_path = _relative(preread_path)
    marker, marker_raw = _read_json(root/marker_path)
    readback, _ = _read_json(activation_readback_path)
    paths = {'plan': plan_path, 'complete_freeze': freeze_path, 'execution_preread': preread_path}
    values = {name:_read_json(root/path)[0] for name,path in paths.items()}
    custody = _custody_module(root)
    manifest, custody_sha256, custody_arguments = _custody_contract(values['complete_freeze'],custody)
    _activation_git_contract(values['complete_freeze'],manifest)
    custody.validate_activation_runtime(manifest, expected_manifest_sha256=custody_sha256, **custody_arguments)
    git_scope = _ActivationGitScope(root, _absolute(values['complete_freeze']['executables']['git']['resolved']))
    def git(*arguments): return _git(root,*arguments,activation_scope=git_scope)
    try:
        receipt = _verify_marker_git_phase(root,paths,values,marker,marker_raw,readback,
            execution_scope=execution_scope,marker_path=marker_path,git=git,custody_sha256=custody_sha256)
    finally:
        git_scope.close()
    custody.validate_material_runtime(manifest,expected_manifest_sha256=custody_sha256)
    receipt['activation_only_runtime_complete'] = True
    return receipt


def _verify_marker_git_phase(root,paths,values,marker,marker_raw,readback,*,
        execution_scope,marker_path,git,custody_sha256):
    head = _commit(git('rev-parse', 'HEAD'), 'activation HEAD')
    if head == SPENT_ACTIVATION_COMMIT:
        raise ValueError('The failed historical activation commit is permanently spent')
    parents = git('rev-list', '--parents', '-n', '1', head).split()
    if len(parents) != 2 or parents[0] != head:
        raise ValueError('Activation must have exactly one parent')
    parent = _commit(parents[1], 'preread parent')
    if git('diff-tree', '--no-commit-id', '--name-only', '-r', head).splitlines() != [marker_path]:
        raise ValueError('Activation commit may change only the unique marker')
    if git('diff-tree', '--no-commit-id', '--name-status', '-r', head) != 'A\t'+marker_path:
        raise ValueError('Activation marker must be a new file, never reused or edited')
    parent_tree = git('rev-parse', parent+'^{tree}')
    marker_blob = git('rev-parse', head+':'+marker_path)
    if git('hash-object',marker_path) != marker_blob:
        raise ValueError('Checked-out activation marker differs from activation commit')

    blobs = {name: git('rev-parse', parent+':'+path) for name, path in paths.items()}
    for name,path in paths.items():
        if git('hash-object',path) != blobs[name]:
            raise ValueError('Checked-out evidence differs from preread parent: '+name)
    expected_marker_keys = {'schema','namespace','activate','preread_commit',
        'preread_tree','plan_sha256','complete_freeze_sha256',
        'execution_preread_sha256','independent_preread_readback',
        'one_control_invocation','control_scope',*DISABLED}
    if set(marker) != expected_marker_keys or marker['schema'] != SCHEMA or marker['namespace'] != NAMESPACE:
        raise ValueError('Exact activation marker schema required')
    if marker['activate'] is not True or marker['one_control_invocation'] is not True:
        raise ValueError('Exactly one engineering control activation required')
    if _absolute(marker['control_scope']) != execution_scope:
        raise ValueError('Marker does not bind the exact outer control scope')
    if marker['preread_commit'] != parent or marker['preread_tree'] != parent_tree:
        raise ValueError('Marker must bind its exact preread parent and tree')
    for key in DISABLED:
        if marker[key] is not False:
            raise ValueError('Activation marker grants forbidden authority: '+key)
    for name, key in (('plan','plan_sha256'),('complete_freeze','complete_freeze_sha256'),
            ('execution_preread','execution_preread_sha256')):
        if marker[key] != _pin_value(values[name]):
            raise ValueError('Marker canonical pin differs: '+name)
    proof = marker['independent_preread_readback']
    if (type(proof) is not dict or set(proof) != {'verified','commit','tree','blobs'}
            or proof['verified'] is not True or proof['commit'] != parent
            or proof['tree'] != parent_tree or proof['blobs'] != blobs):
        raise ValueError('Exact independent preread readback required')
    expected_readback = {'schema':READBACK_SCHEMA,'repository':REPOSITORY,
        'branch':BRANCH,'verified':True,'activation_commit':head,
        'activation_tree':git('rev-parse',head+'^{tree}'),
        'activation_parent':parent,'marker_path':marker_path,
        'marker_blob':marker_blob,'marker_sha256':hashlib.sha256(marker_raw).hexdigest()}
    if canonical(readback) != canonical(expected_readback):
        raise ValueError('Exact independent public activation readback required')
    receipt = {'schema':RECEIPT_SCHEMA,'namespace':NAMESPACE,
        'activation_commit':head,'activation_tree':readback['activation_tree'],
        'activation_parent':parent,'activation_public_readback_verified':True,
        'marker_path':marker_path,'marker_blob':marker_blob,
        'marker_sha256':readback['marker_sha256'],
        'plan_sha256':marker['plan_sha256'],
        'complete_freeze_sha256':marker['complete_freeze_sha256'],
        'execution_preread_sha256':marker['execution_preread_sha256'],
        'control_scope':execution_scope,'runtime_custody_manifest_sha256':custody_sha256,
        'activation_only_runtime_complete':False,
        'one_control_invocation':True, **{key:False for key in DISABLED}}
    return receipt


def validate_worker_receipt(receipt, *, plan, complete_freeze, execution_preread,
        execution_scope=None):
    """Recheck the immutable outer receipt before a worker may write anything."""
    expected_keys = {'schema','namespace','activation_commit','activation_tree',
        'activation_parent','activation_public_readback_verified','marker_path',
        'marker_blob','marker_sha256','plan_sha256','complete_freeze_sha256',
        'execution_preread_sha256','one_control_invocation','control_scope',
        'runtime_custody_manifest_sha256','activation_only_runtime_complete',*DISABLED}
    if type(receipt) is not dict or set(receipt) != expected_keys:
        raise ValueError('Exact activation receipt structure required')
    if receipt['schema'] != RECEIPT_SCHEMA or receipt['namespace'] != NAMESPACE:
        raise ValueError('Exact activation receipt identity required')
    if receipt['marker_path'] == SPENT_MARKER or receipt['activation_commit'] == SPENT_ACTIVATION_COMMIT:
        raise ValueError('Historical failed activation receipt is permanently spent')
    for key in ('activation_commit','activation_parent'):
        _commit(receipt[key], key)
    _sha(receipt['marker_sha256'],'marker'); _sha(receipt['plan_sha256'],'plan')
    _sha(receipt['complete_freeze_sha256'],'freeze'); _sha(receipt['execution_preread_sha256'],'preread')
    if type(receipt['activation_tree']) is not str or not COMMIT.fullmatch(receipt['activation_tree']):
        raise ValueError('Exact Git activation tree required')
    if type(receipt['marker_blob']) is not str or not COMMIT.fullmatch(receipt['marker_blob']):
        raise ValueError('Exact Git activation marker blob required')
    if (receipt['activation_public_readback_verified'] is not True
            or receipt['one_control_invocation'] is not True
            or receipt['marker_path'] != MARKER):
        raise ValueError('One public marker-only activation receipt required')
    scope = _absolute(receipt['control_scope'])
    if execution_scope is not None and scope != _absolute(execution_scope):
        raise ValueError('Worker activation receipt control scope differs')
    if receipt['activation_only_runtime_complete'] is not True:
        raise ValueError('Activation-only Git phase must be complete before material workers')
    for key in DISABLED:
        if receipt[key] is not False:
            raise ValueError('Activation receipt grants forbidden authority: '+key)
    for key, value in (('plan_sha256',plan),('complete_freeze_sha256',complete_freeze),
            ('execution_preread_sha256',execution_preread)):
        if receipt[key] != _pin_value(value):
            raise ValueError('Worker activation receipt pin differs: '+key)
    custody = _custody_module(Path(__file__).resolve().parents[1])
    manifest,digest,_ = _custody_contract(complete_freeze,custody)
    if _sha(receipt['runtime_custody_manifest_sha256'],'runtime custody receipt') != digest:
        raise ValueError('Worker activation receipt runtime custody hash differs')
    custody.validate_material_runtime(manifest,expected_manifest_sha256=digest)
    return True
