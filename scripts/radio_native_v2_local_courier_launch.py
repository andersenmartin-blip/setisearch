#!/usr/bin/env python3
"""Short, pinned local courier launch. All execution authority remains false."""
import argparse
import hashlib
import json
import os
from pathlib import Path


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
                                               'results_radio_native_v2_local_transport_20260930a/live02')
            or options.get('cases') != 1 or options.get('root') != str(root)):
        raise ValueError('Only the fixed single-case prospective fixture is supported')
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
