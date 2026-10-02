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
import subprocess

SCHEMA = 'radio-native-v2-control-single-activation-v1'
RECEIPT_SCHEMA = 'radio-native-v2-control-single-activation-receipt-v1'
READBACK_SCHEMA = 'radio-native-v2-control-single-activation-public-readback-v1'
NAMESPACE = 'radio-native-v2-control-activation-transition-20261002a'
REPOSITORY = 'andersenmartin-blip/setisearch'
BRANCH = 'm43-support-qualification'
MARKER = 'config/radio_native_v2_control_activation_20261002a.activate.json'
DISABLED = ('reservation_authorized', 'rng_authorized',
    'scientific_execution_authorized', 'native_execution_authorized',
    'restart_authorized', 'automatic_retry')
HASH = re.compile(r'[0-9a-f]{64}\Z')
COMMIT = re.compile(r'[0-9a-f]{40}\Z')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode()


def _git(root, *arguments):
    environment = {key: value for key, value in os.environ.items()
        if not key.startswith('GIT_')}
    environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
        GIT_CONFIG_SYSTEM='/dev/null', GIT_NO_REPLACE_OBJECTS='1')
    return subprocess.check_output(['git', '--no-replace-objects', *arguments],
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


def _read_json(path, maximum=1024*1024):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Regular non-symlink activation JSON required')
    raw = path.read_bytes()
    if not raw or len(raw) > maximum:
        raise ValueError('Bounded nonempty activation JSON required')
    value = json.loads(raw, object_pairs_hook=_unique)
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
        activation_readback_path, marker_path=MARKER):
    """Verify one public marker-only child and return a bounded worker receipt."""
    root = Path(root).resolve(); marker_path = _relative(marker_path)
    plan_path = _relative(plan_path); freeze_path = _relative(freeze_path)
    preread_path = _relative(preread_path)
    marker, marker_raw = _read_json(root/marker_path)
    readback, _ = _read_json(activation_readback_path)
    head = _commit(_git(root, 'rev-parse', 'HEAD'), 'activation HEAD')
    parents = _git(root, 'rev-list', '--parents', '-n', '1', head).split()
    if len(parents) != 2 or parents[0] != head:
        raise ValueError('Activation must have exactly one parent')
    parent = _commit(parents[1], 'preread parent')
    if _git(root, 'diff-tree', '--no-commit-id', '--name-only', '-r', head).splitlines() != [marker_path]:
        raise ValueError('Activation commit may change only the unique marker')
    if _git(root, 'diff-tree', '--no-commit-id', '--name-status', '-r', head) != 'A\t'+marker_path:
        raise ValueError('Activation marker must be a new file, never reused or edited')
    parent_tree = _git(root, 'rev-parse', parent+'^{tree}')
    marker_blob = _git(root, 'rev-parse', head+':'+marker_path)
    if _git(root,'hash-object',marker_path) != marker_blob:
        raise ValueError('Checked-out activation marker differs from activation commit')

    paths = {'plan': plan_path, 'complete_freeze': freeze_path,
        'execution_preread': preread_path}
    values = {name: _read_json(root/path)[0] for name, path in paths.items()}
    blobs = {name: _git(root, 'rev-parse', parent+':'+path) for name, path in paths.items()}
    for name,path in paths.items():
        if _git(root,'hash-object',path) != blobs[name]:
            raise ValueError('Checked-out evidence differs from preread parent: '+name)
    expected_marker_keys = {'schema','namespace','activate','preread_commit',
        'preread_tree','plan_sha256','complete_freeze_sha256',
        'execution_preread_sha256','independent_preread_readback',
        'one_control_invocation',*DISABLED}
    if set(marker) != expected_marker_keys or marker['schema'] != SCHEMA or marker['namespace'] != NAMESPACE:
        raise ValueError('Exact activation marker schema required')
    if marker['activate'] is not True or marker['one_control_invocation'] is not True:
        raise ValueError('Exactly one engineering control activation required')
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
        'activation_tree':_git(root,'rev-parse',head+'^{tree}'),
        'activation_parent':parent,'marker_path':marker_path,
        'marker_blob':marker_blob,'marker_sha256':hashlib.sha256(marker_raw).hexdigest()}
    if readback != expected_readback:
        raise ValueError('Exact independent public activation readback required')
    receipt = {'schema':RECEIPT_SCHEMA,'namespace':NAMESPACE,
        'activation_commit':head,'activation_tree':readback['activation_tree'],
        'activation_parent':parent,'activation_public_readback_verified':True,
        'marker_path':marker_path,'marker_blob':marker_blob,
        'marker_sha256':readback['marker_sha256'],
        'plan_sha256':marker['plan_sha256'],
        'complete_freeze_sha256':marker['complete_freeze_sha256'],
        'execution_preread_sha256':marker['execution_preread_sha256'],
        'one_control_invocation':True, **{key:False for key in DISABLED}}
    return receipt


def validate_worker_receipt(receipt, *, plan, complete_freeze, execution_preread):
    """Recheck the immutable outer receipt before a worker may write anything."""
    expected_keys = {'schema','namespace','activation_commit','activation_tree',
        'activation_parent','activation_public_readback_verified','marker_path',
        'marker_blob','marker_sha256','plan_sha256','complete_freeze_sha256',
        'execution_preread_sha256','one_control_invocation',*DISABLED}
    if type(receipt) is not dict or set(receipt) != expected_keys:
        raise ValueError('Exact activation receipt structure required')
    if receipt['schema'] != RECEIPT_SCHEMA or receipt['namespace'] != NAMESPACE:
        raise ValueError('Exact activation receipt identity required')
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
    for key in DISABLED:
        if receipt[key] is not False:
            raise ValueError('Activation receipt grants forbidden authority: '+key)
    for key, value in (('plan_sha256',plan),('complete_freeze_sha256',complete_freeze),
            ('execution_preread_sha256',execution_preread)):
        if receipt[key] != _pin_value(value):
            raise ValueError('Worker activation receipt pin differs: '+key)
    return True
