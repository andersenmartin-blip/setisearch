#!/usr/bin/env python3
"""Validate a single marker-only, independently read-back engineering activation.

This is publication engineering only. It never imports the native runner,
reserves a case, creates a random generator, or opens telescope data.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

NAMESPACE = 'radio-native-v2-actions-control-20261001a'
REPOSITORY = 'andersenmartin-blip/setisearch'
BRANCH = 'm43-support-qualification'
MARKER = 'config/radio_native_v2_actions_control_20261001a.activate.json'
MANIFEST = 'config/radio_native_v2_actions_control_20261001a.manifest.json'
REQUIRED_FILES = frozenset((
    '.github/workflows/radio_native_v2_actions_control_20261001a.yml',
    'scripts/radio_native_v2_actions_activation_gate.py',
    'scripts/radio_native_v2_actions_publisher_control.py',
    'scripts/radio_native_v2_actions_supervisor.py',
    'config/radio_native_v2_actions_control_20261001a.protocol.json',
))
DISABLED = ('reservation_authorized', 'rng_authorized', 'execution_authorized',
            'scientific_execution_authorized', 'restart_authorized',
            'transport_integration_qualified')


def git(root, *arguments):
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith('GIT_')}
    environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
                       GIT_CONFIG_SYSTEM='/dev/null')
    return subprocess.check_output(
        ['git', '--no-replace-objects', *arguments], cwd=root,
        env=environment).decode().strip()


def verify(root, environment):
    root = Path(root).resolve()
    if (environment.get('GITHUB_REPOSITORY') != REPOSITORY
            or environment.get('GITHUB_REF') != 'refs/heads/' + BRANCH
            or environment.get('GITHUB_EVENT_NAME') != 'push'
            or environment.get('GITHUB_RUN_ATTEMPT') != '1'):
        raise ValueError('Only the first attempt of the fixed public branch push is permitted')
    activation = environment.get('GITHUB_SHA', '')
    if not re.fullmatch('[0-9a-f]{40}', activation) or git(root, 'rev-parse', 'HEAD') != activation:
        raise ValueError('Activation checkout is not the exact event commit')
    marker = json.loads((root / MARKER).read_text())
    if marker.get('namespace') != NAMESPACE or marker.get('activate') is not True:
        raise ValueError('Wrong engineering activation namespace')
    preparation = marker.get('preparation_commit', '')
    if not re.fullmatch('[0-9a-f]{40}', preparation):
        raise ValueError('An immutable preparation commit is required')
    if git(root, 'rev-parse', activation + '^') != preparation:
        raise ValueError('Activation must be a direct child of the read-back preparation')
    if git(root, 'rev-list', '--parents', '-n', '1', activation).split() != [activation, preparation]:
        raise ValueError('Activation must have exactly one preparation parent')
    if git(root, 'diff-tree', '--no-commit-id', '--name-only', '-r', activation).splitlines() != [MARKER]:
        raise ValueError('Activation must add only its unique marker')
    if git(root, 'diff-tree', '--no-commit-id', '--name-status', '-r', activation) != 'A\t' + MARKER:
        raise ValueError('The activation marker may not be reused or edited')
    raw = (root / MANIFEST).read_bytes()
    manifest_sha = hashlib.sha256(raw).hexdigest()
    if marker.get('manifest_sha256') != manifest_sha:
        raise ValueError('Manifest differs from independent preparation readback')
    manifest = json.loads(raw)
    proof = marker.get('independent_readback', {})
    if (manifest.get('namespace') != NAMESPACE or proof.get('commit') != preparation
            or proof.get('verified') is not True
            or proof.get('manifest_sha256') != manifest_sha):
        raise ValueError('Missing exact independent preparation readback')
    expected = manifest.get('files', [])
    if (len(expected) != len(REQUIRED_FILES)
            or {item.get('path') for item in expected} != REQUIRED_FILES
            or proof.get('files') != expected):
        raise ValueError('Readback must bind every prepared code, protocol and workflow file')
    for item in expected:
        relative = item['path']
        path = root / relative
        if (Path(relative).is_absolute() or '..' in Path(relative).parts
                or path.is_symlink() or not path.is_file()
                or not path.resolve().is_relative_to(root)):
            raise ValueError('Unsafe preparation file')
        data = path.read_bytes()
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Prepared file changed: ' + relative)
    for source in (marker, manifest):
        if any(source.get(key) is not False for key in DISABLED):
            raise ValueError('Engineering controls cannot grant native or scientific authority')
    return {'schema': 'radio-native-v2-actions-activation-readback-v1',
            'namespace': NAMESPACE, 'preparation_commit': preparation,
            'activation_commit': activation, 'manifest_sha256': manifest_sha,
            'verified': True, **{key: False for key in DISABLED}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = verify(args.root, os.environ)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as target:
        target.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
