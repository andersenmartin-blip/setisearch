#!/usr/bin/env python3
"""Short, pinned local courier launch. All execution authority remains false."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat


NETWORK_SCHEMA = 'radio-native-v2-pinned-git-fetch-network-policy-v1'
CA_PATH = 'config/radio_native_v2_local_git_ca_20260930.pem'
PROXY_POLICY = {'source_environment_key': 'HTTPS_PROXY', 'scheme': 'http', 'hostname': '127.0.0.1',
                'minimum_port': 1, 'maximum_port': 65535, 'credentials_allowed': False,
                'path_allowed': False, 'query_allowed': False, 'fragment_allowed': False}


def _pinned_input(path, expected_sha256, maximum_bytes, expected_bytes=None):
    path = Path(path)
    if (not path.is_absolute() or str(path) != os.path.normpath(str(path))
            or not isinstance(expected_sha256, str) or not re.fullmatch('[0-9a-f]{64}', expected_sha256)):
        raise ValueError('Canonical pinned network input required')
    for parent in path.parents:
        if parent.is_symlink() or not parent.is_dir():
            raise ValueError('Symlinked network input ancestor refused')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_size > maximum_bytes
                or (expected_bytes is not None and before.st_size != expected_bytes)):
            raise ValueError('Bounded sole network input required')
        with os.fdopen(fd, 'rb', closefd=False) as source:
            raw = source.read(maximum_bytes + 1)
        if (len(raw) != before.st_size or os.fstat(fd).st_size != before.st_size
                or hashlib.sha256(raw).hexdigest() != expected_sha256):
            raise ValueError('Pinned network input drifted')
        return raw
    finally:
        os.close(fd)


def validate_runtime_proxy(value):
    if (not isinstance(value, str) or not re.fullmatch(r'http://127\.0\.0\.1:[1-9][0-9]{0,4}', value)
            or int(value.rsplit(':', 1)[1]) > 65535):
        raise ValueError('Credential-free exact loopback HTTPS_PROXY required')
    return value


def capture_git_network_proxy(root, config_path, config_sha256):
    """Select one current endpoint; no other inherited environment survives."""
    if str(config_path) != str(root / 'config/radio_native_v2_local_git_network_20260930.json'):
        raise ValueError('Exact repository network policy path required')
    raw = _pinned_input(config_path, config_sha256, 16384)
    policy = json.loads(raw)
    if raw != json.dumps(policy, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode():
        raise ValueError('Canonical network policy required')
    fields = {'schema', 'repository', 'operation', 'proxy_policy', 'tls_ca', 'automatic_retry',
              'execution_authorized', 'reservation_authorized', 'scientific_execution_authorized'}
    if (not isinstance(policy, dict) or set(policy) != fields or policy['schema'] != NETWORK_SCHEMA
            or policy['repository'] != 'andersenmartin-blip/setisearch' or policy['operation'] != 'git_fetch'
            or json.dumps(policy['proxy_policy'], sort_keys=True, separators=(',', ':'))
               != json.dumps(PROXY_POLICY, sort_keys=True, separators=(',', ':'))
            or any(policy[key] is not False for key in fields if key.endswith('_authorized') or key == 'automatic_retry')):
        raise ValueError('Exact non-authorizing Git fetch network policy required')
    ca = policy['tls_ca']
    if (not isinstance(ca, dict) or set(ca) != {'path', 'bytes', 'sha256'} or ca['path'] != CA_PATH
            or type(ca['bytes']) is not int or not 0 < ca['bytes'] <= 4 * 1024 * 1024):
        raise ValueError('Exact pinned repository TLS CA required')
    _pinned_input(root / ca['path'], ca['sha256'], 4 * 1024 * 1024, ca['bytes'])
    return validate_runtime_proxy(os.environ.get('HTTPS_PROXY'))


def prepare(root, freeze_path, freeze_sha256, config_path, config_sha256):
    from radio_native_v2_node_loader import prepare_launch
    from radio_native_v2_source_loader import prepare_helper_launch
    root, freeze_path, config_path = map(lambda p: Path(p).resolve(),
                                        (root, freeze_path, config_path))
    raw = config_path.read_bytes()
    if len(raw) > 64 * 1024 or hashlib.sha256(raw).hexdigest() != config_sha256:
        raise ValueError('Bounded exact prospective controller configuration required')
    options = json.loads(raw)
    if (options.get('fixture_namespace') not in ('results_radio_native_v2_local_transport_20260930a/live01',
                                               'results_radio_native_v2_local_transport_20260930a/live02',
                                               'results_radio_native_v2_local_transport_20260930a/live03',
                                               'results_radio_native_v2_local_transport_20260930a/live04')
            or options.get('cases') != 1 or options.get('root') != str(root)):
        raise ValueError('Only the fixed single-case prospective fixture is supported')
    if 'gitNetworkRuntimeProxy' in options:
        raise ValueError('Runtime proxy must be selected from this launcher environment')
    network_keys = {'gitNetworkConfigPath', 'gitNetworkConfigSha256'}
    supplied_network_keys = network_keys.intersection(options)
    if supplied_network_keys:
        if supplied_network_keys != network_keys:
            raise ValueError('Complete pinned network policy options required')
        options['gitNetworkRuntimeProxy'] = capture_git_network_proxy(
            root, options['gitNetworkConfigPath'], options['gitNetworkConfigSha256'])
    template = options.pop('start_arguments_template', None)
    if (not isinstance(template, dict) or not isinstance(template.get('cmd'), str)
            or template['cmd'].count('__CONFIG_SHA256__') != 1
            or template.get('tty') is not True):
        raise ValueError('Exact prospective startup argument template required')
    start_arguments = {**template, 'cmd': template['cmd'].replace('__CONFIG_SHA256__', config_sha256)}
    helper = prepare_helper_launch(root, freeze_path, freeze_sha256)
    options = {**options, 'helperLaunch': helper, 'startRequest': json.dumps({
        'tool': 'exec_command', 'arguments': start_arguments}, separators=(',', ':'), ensure_ascii=True)}
    sources = ('scripts/radio_native_v2_local_courier.js',
               'scripts/radio_native_v2_local_worker.js',
               'scripts/radio_native_v2_local_transport.js',
               'scripts/radio_native_v2_local_git.js',
               'scripts/radio_native_v2_broker_host.js')
    return prepare_launch(root, freeze_path, freeze_sha256, modules=(),
                          source_paths=sources, entrypoint={
                              'module': sources[0], 'export': 'main', 'options': options})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--freeze-path', required=True)
    parser.add_argument('--freeze-sha256', required=True)
    parser.add_argument('--config-path', required=True)
    parser.add_argument('--config-sha256', required=True)
    args = parser.parse_args()
    plan = prepare(args.root, args.freeze_path, args.freeze_sha256,
                   args.config_path, args.config_sha256)
    # The real tool retains stdin only for a TTY; remove echo/canonical buffering
    # before the pinned child starts, without embedding payloads in shell argv.
    if os.isatty(0):
        import tty
        tty.setraw(0)
    os.chdir(plan['cwd'])
    os.execve(plan['arguments'][0], plan['arguments'], plan['environment'])
