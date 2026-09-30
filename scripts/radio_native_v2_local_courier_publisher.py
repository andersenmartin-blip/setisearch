#!/usr/bin/env python3
"""One fixed non-scientific transport control through the unchanged Publisher.

The pinned parent starts this component only after independent public code
readback. Runtime arguments identify immutable Git objects and private paths;
they grant no native reservation, execution, restart or scientific authority.
"""
import hashlib
import json
import resource
import subprocess
import sys
import time
from pathlib import Path

from seti_repeater import native_v2_broker_radio as broker
from seti_repeater.native_v2_bridge_radio import Store, Worker
from seti_repeater.empty_null_radio import canonical
from radio_native_v2_local_transport_fixture import deterministic_bundle, PREFIX

SOURCE_BYTES = 65536
CONTROL_PREFIX = 'results_radio_native_v2_local_transport_20260930a/live02'
SCHEMA = 'radio-native-v2-actual-tool-courier-publisher-control-v1'


def main():
    policy = getattr(sys, '_radio_native_v2_source_policy_preflight', None)
    if not policy or policy.get('execution_authorized') is not False:
        raise ValueError('Pinned source-only component launch required')
    raw = sys.stdin.buffer.readline(65537)
    if len(raw) > 65536 or not raw.endswith(b'\n'):
        raise ValueError('Bounded exact transport control configuration required')
    config = json.loads(raw)
    if set(config) != {'parent', 'parent_tree', 'repository_path', 'store_root', 'result_path',
                       'code_commit', 'freeze_sha256'} or canonical(config)+b'\n' != raw:
        raise ValueError('Exact canonical transport control configuration required')
    if (config['parent'] != config['code_commit'] or config['freeze_sha256'] != policy['freeze_sha256']
            or any(len(config[key]) != 40 or any(ch not in '0123456789abcdef' for ch in config[key])
                   for key in ('parent', 'parent_tree', 'code_commit'))):
        raise ValueError('Independently read-back immutable code parent required')
    for key in ('repository_path', 'store_root', 'result_path'):
        path = Path(config[key])
        if not path.is_absolute() or path.resolve() != path:
            raise ValueError('Canonical private control path required')
    freeze_raw = Path(sys.argv[-3]).read_bytes()
    if hashlib.sha256(freeze_raw).hexdigest() != policy['freeze_sha256']:
        raise ValueError('Pinned runtime freeze differs before Git parent validation')
    git_path = json.loads(freeze_raw)['executables']['git']['invocation']
    commit = subprocess.run([git_path, '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
                             'cat-file', 'commit', config['parent']], cwd=config['repository_path'],
                            env={'PATH': '/usr/bin:/bin', 'GIT_CONFIG_NOSYSTEM': '1',
                                 'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_CONFIG_GLOBAL': '/dev/null',
                                 'GIT_NO_LAZY_FETCH': '1'}, capture_output=True, timeout=30)
    data = commit.stdout
    if (commit.returncode or hashlib.sha1(('commit '+str(len(data))+'\0').encode()+data).hexdigest() != config['parent']
            or not data.startswith(('tree '+config['parent_tree']+'\n').encode())):
        raise ValueError('Actual immutable local Git parent/tree differs')
    broker.ROOT_PREFIX = CONTROL_PREFIX  # This process cannot use the native namespace.
    started = time.monotonic()
    worker = Worker(Store(config['store_root']))
    invoker = broker.DurableInvoker(worker.invoke, worker.persist)
    cumulative = broker.CumulativeBroker(invoker.invoke)
    error = None; receipt = None; host_receipt = None
    try:
        bundle = deterministic_bundle(0, SOURCE_BYTES, config['parent'], config['parent_tree'], namespace=CONTROL_PREFIX)
        worker.prepare_transport(bundle.freeze_bytes.decode(), bundle.sha256)
        receipt = cumulative.publish(bundle)
        host_receipt = worker.finish_transport()
        if (receipt['commit'] != host_receipt['commit'] or receipt['tree'] != host_receipt['tree']
                or bundle.sha256 != host_receipt['bundle_sha256']):
            raise ValueError('Actual host/Publisher immutable result binding differs')
        worker.persist_state({'schema': SCHEMA, 'publisher': receipt, 'host': host_receipt,
                              'execution_authorized': False})
    except BaseException as failure:
        error = repr(failure)
    result = {'schema': SCHEMA, 'mode': 'ACTUAL_TOOL_TRANSPORT_CONTROL_ONLY',
              'status': 'PASSED' if error is None else 'STOPPED', 'error': error,
              'source_bytes': SOURCE_BYTES, 'prefix': CONTROL_PREFIX, 'parent_code_commit': config['code_commit'],
              'publisher': receipt, 'host': host_receipt, 'worker_requests': worker.ordinal,
              'python_broker_usage': cumulative.usage(), 'durable_python_receipts': invoker.records,
              'source_loader_preflight': policy, 'elapsed_seconds': time.monotonic()-started,
              'python_pid': __import__('os').getpid(),
              'python_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
              'public_mutations_directly_performed_by_python': 0,
              'external_mutation_receipts_required': True, 'native_case_reservations': 0,
              'rng_draws': 0, 'telescope_reads': 0, 'automatic_retry': False,
              'execution_authorized': False, 'reservation_authorized': False,
              'scientific_execution_authorized': False}
    destination = Path(config['result_path'])
    with destination.open('xb') as stream:
        stream.write(canonical(result)); stream.flush()
        import os
        os.fsync(stream.fileno())
    print(canonical({'schema': SCHEMA, 'status': result['status']}).decode(), flush=True)


if __name__ == '__main__':
    main()
