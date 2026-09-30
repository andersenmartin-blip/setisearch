#!/usr/bin/env python3
"""Deterministic closed transport fixture using the unchanged Publisher.

Only a new temporary Git repository and an isolated fixture namespace are
written. Payload bytes are arithmetic constants, never telescope data or RNG.
The copied source-only policy is an import/component proof, not execution
authority. This API is reusable by the real-tool courier's engineering harness.
"""
from dataclasses import asdict
import argparse
import base64
import gc
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import sysconfig
import time
from types import MappingProxyType

from seti_repeater.empty_null_radio import canonical
from seti_repeater import native_v2_broker_radio as broker
from seti_repeater.native_v2_bridge_radio import Store, Worker

SCHEMA = 'radio-native-v2-local-transport-fixture-v1'
PREFIX = 'results_radio_native_v2_local_transport_20260930a/live01'
DISABLED = ('reservation_authorized', 'rng_authorized', 'execution_authorized',
            'scientific_execution_authorized', 'restart_authorized', 'transport_integration_qualified')


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())


def _git(path, *args, data=None):
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_SYSTEM': '/dev/null',
           'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_AUTHOR_NAME': 'Closed transport fixture',
           'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
           'GIT_COMMITTER_NAME': 'Closed transport fixture',
           'GIT_COMMITTER_EMAIL': 'fixture@example.invalid',
           'GIT_AUTHOR_DATE': '2000-01-01T00:00:00Z', 'GIT_COMMITTER_DATE': '2000-01-01T00:00:00Z'}
    result = subprocess.run(['/usr/bin/git', '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
                             '-c', 'gc.auto=0', *args], cwd=path, env=env,
                            input=data, capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError('Closed local Git fixture command failed: '+result.stderr.decode()[-1000:])
    return result.stdout.decode().strip()


def prepare_fixture(directory, *, source_bytes=broker.MAX_SOURCE_BYTES, cases=2, repository_root=None):
    """Create reusable fixed config, source-only launch plans and local Git.

    There is no native case reservation and no network operation. Code is
    copied before it is pinned, so concurrent development cannot change a
    fixture's executable buffers while its helper is running.
    """
    directory = Path(directory).absolute()
    if type(source_bytes) is not int or not 1 <= source_bytes <= broker.MAX_SOURCE_BYTES or type(cases) is not int or not 1 <= cases <= 8:
        raise ValueError('Fixed bounded deterministic fixture size/case count required')
    directory.mkdir(mode=0o700)
    origin = Path(repository_root or Path(__file__).resolve().parents[1])
    code_root = directory/'frozen-code'; code_root.mkdir()
    code = {}
    for group in ('src', 'scripts'):
        for path in sorted((origin/group).rglob('*')):
            if path.is_file() and path.suffix in ('.py', '.js', '.mjs', '.cjs') and '__pycache__' not in path.parts:
                relative = path.relative_to(origin)
                raw = path.read_bytes(); _write(code_root/relative, raw)
                code[str(relative)] = hashlib.sha256(raw).hexdigest()
    repo = directory/'git'; repo.mkdir()
    _git(repo, 'init', '-q')
    blob = _git(repo, 'hash-object', '-w', '--stdin', data=b'Deterministic closed fixture parent\n')
    _git(repo, 'update-index', '--add', '--cacheinfo', '100644,'+blob+',fixture.txt')
    parent_tree = _git(repo, 'write-tree')
    parent = _git(repo, 'commit-tree', parent_tree, data=b'Closed fixture parent\n')
    _git(repo, 'update-ref', 'refs/heads/'+broker.BRANCH, parent)
    (directory/'git-spool').mkdir()
    store_root = directory/'store'; Store.create(str(store_root))
    config = {'schema': SCHEMA, 'fixture_root': str(directory), 'code_root': str(code_root),
              'repository_path': str(repo), 'store_root': str(store_root),
              'spool_root': str(directory/'git-spool'), 'source_bytes': source_bytes,
              'cases': cases, 'prefix': PREFIX, 'parent': parent, 'parent_tree': parent_tree,
              'rng_draws': 0, 'telescope_reads': 0, 'native_case_reservations': 0,
              **{key: False for key in DISABLED}}
    config_path = code_root/'fixture-worker-config.json'; _write(config_path, canonical(config))
    # Source-only preflight pins every importable Python/NumPy source and
    # extension. Full ELF/runtime/network qualification remains a separate gate.
    stdlib = Path(sysconfig.get_path('stdlib'))
    runtime = {}
    for path in sorted(stdlib.rglob('*')):
        parts = path.relative_to(stdlib).parts
        if (path.is_file() and path.suffix in ('.py', '.so') and '__pycache__' not in path.parts
                and ('site-packages' not in parts or
                     (len(parts) > 1 and parts[0] == 'site-packages' and parts[1] in ('numpy', 'numpy.libs')))):
            runtime[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    executable = str(Path(sys.executable).resolve())
    runtime[executable] = hashlib.sha256(Path(executable).read_bytes()).hexdigest()
    git_path = str(Path('/usr/bin/git').resolve())
    node_path = str(Path(shutil.which('node')).resolve())
    freeze = {'mode': 'PROSPECTIVE_ENGINEERING_ONLY', **{key: False for key in DISABLED},
              'runtime_sha256s': runtime, 'code_sha256s': code,
              'input_sha256s': {'fixture-worker-config.json': hashlib.sha256(config_path.read_bytes()).hexdigest()},
              'executables': {'python': {'invocation': sys.executable, 'resolved': executable,
                  'sha256': runtime[executable], 'version': sys.version},
                  'git': {'invocation': git_path}, 'node': {'invocation': node_path}}}
    freeze_path = directory/'source-freeze.json'; raw = canonical(freeze); _write(freeze_path, raw)
    freeze_sha = hashlib.sha256(raw).hexdigest()
    from radio_native_v2_source_loader import prepare_helper_launch
    helper_launch = prepare_helper_launch(code_root, freeze_path, freeze_sha)
    worker_launch = prepare_helper_launch(code_root, freeze_path, freeze_sha,
                                         module='radio_native_v2_local_transport_fixture')
    prepared = {**config, 'python': sys.executable, 'node': node_path, 'git_path': git_path,
                'freeze_path': str(freeze_path), 'freeze_sha256': freeze_sha,
                'config_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest(),
                'helper_launch': helper_launch, 'worker_launch': worker_launch,
                'source_inventory_files': len(code), 'runtime_inventory_files': len(runtime)}
    _write(directory/'prepared.json', canonical(prepared))
    return prepared


def deterministic_bundle(ordinal, source_bytes, parent, tree):
    """A genuine framed Bundle for Publisher, deliberately no scientific map."""
    if (type(ordinal) is not int or not 0 <= ordinal < 8 or type(source_bytes) is not int
            or not 1 <= source_bytes <= broker.MAX_SOURCE_BYTES):
        raise ValueError('Bounded deterministic fixture framing required')
    case_identity = hashlib.sha256(('closed-local-transport-fixture-'+str(ordinal)).encode()).hexdigest()
    target = PREFIX+f'/case{ordinal:02d}-{case_identity[:16]}'
    pattern = bytes((index+ordinal) % 256 for index in range(256))
    source = (pattern*(source_bytes//len(pattern)+1))[:source_bytes]
    files = {}; chunks = []
    for index, start in enumerate(range(0, len(source), broker.CHUNK_BYTES)):
        path = target+f'/chunk{index:04d}.b64'; data = base64.b64encode(source[start:start+broker.CHUNK_BYTES])
        files[path] = data
        chunks.append({'path': path, 'stored_bytes': len(data), 'stored_sha256': hashlib.sha256(data).hexdigest()})
    manifest = canonical({'schema': broker.SCHEMA, 'mode': 'ENGINEERING_ONLY', 'repository': broker.REPO,
        'branch': broker.BRANCH, 'prefix': target, 'ordinal': ordinal, 'case_identity': case_identity,
        'source_summary': {'schema': SCHEMA, 'fixture_only': True, 'native_case': False},
        'sources': {'fixture/deterministic_payload.bin': {'offset': 0, 'bytes': len(source),
                    'sha256': hashlib.sha256(source).hexdigest()}},
        'source_bytes': len(source), 'source_sha256': hashlib.sha256(source).hexdigest(),
        'chunk_bytes': broker.CHUNK_BYTES, 'chunks': chunks,
        'execution_restart_authorized': False, 'scientific_admission_authorized': False})
    files[target+'/manifest.json'] = manifest
    files[target+'/HEAD'] = hashlib.sha256(manifest).hexdigest().encode()+b'\n'
    limits = broker.Limits()
    freeze = canonical({'schema': broker.SCHEMA, 'mode': 'ENGINEERING_ONLY', 'repository': broker.REPO,
        'branch': broker.BRANCH, 'broker_protocol': broker.BROKER_PROTOCOL,
        'per_operation_response_reservations': dict(broker.RESPONSE_RESERVATIONS),
        'ordinal': ordinal, 'prefix': target, 'parent': parent, 'parent_tree': tree,
        'limits': asdict(limits), 'files': {path: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
          'blob': hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()} for path, data in sorted(files.items())},
        'manifest_sha256': hashlib.sha256(manifest).hexdigest(), 'single_inline_tree_request': True,
        'single_grouped_readback': True, 'force': False, 'automatic_retry': False,
        'execution_restart_authorized': False, 'scientific_admission_authorized': False})
    return broker.Bundle(ordinal, target, MappingProxyType(files), manifest, freeze, limits)


def publisher_worker(config):
    """Unchanged Worker/DurableInvoker/CumulativeBroker; immutable fixture only."""
    if config['prefix'] != PREFIX or any(config.get(key) is not False for key in DISABLED):
        raise ValueError('Closed fixture configuration grants no authority')
    broker.ROOT_PREFIX = PREFIX  # An isolated fixture process; never native namespace.
    started = time.monotonic(); worker = Worker(Store(config['store_root']))
    durable = broker.DurableInvoker(worker.invoke, worker.persist)
    cumulative = broker.CumulativeBroker(durable.invoke)
    parent, tree = config['parent'], config['parent_tree']; rows = []; error = None
    try:
        for ordinal in range(config['cases']):
            bundle = deterministic_bundle(ordinal, config['source_bytes'], parent, tree)
            worker.prepare_transport(bundle.freeze_bytes.decode(), bundle.sha256)
            receipt = cumulative.publish(bundle)
            host_receipt = worker.finish_transport()
            if (host_receipt['commit'] != receipt['commit'] or host_receipt['tree'] != receipt['tree']
                    or host_receipt['bundle_sha256'] != bundle.sha256):
                raise ValueError('Concrete host/Publisher immutable receipt binding differs')
            row = {'ordinal': ordinal, 'source_bytes': config['source_bytes'], 'publisher': receipt,
                   'host': host_receipt, 'worker_requests': worker.ordinal}
            worker.persist_state({'schema': SCHEMA, 'completed_case': row, 'fixture_only': True})
            rows.append(row); parent, tree = receipt['commit'], receipt['tree']
            del bundle; gc.collect()
    except BaseException as failure:
        error = repr(failure)
        unexpected = {}
        for item in sorted((Path(config['store_root'])/'items').iterdir()):
            names = sorted(path.name for path in item.iterdir())
            if not set(names) <= {'intent.json', 'part', 'sealing.json', 'sealed.json', 'claimed.json'}:
                unexpected[item.name] = names
        _write(Path(config['fixture_root'])/'store-failure-inventory.json', canonical({
            'error': error, 'unexpected_item_files': unexpected,
            'automatic_retry': False, 'payload_bytes_read': 0}))
    result = {'schema': SCHEMA, 'mode': 'OFFLINE_FULL_PUBLISHER_FIXTURE', 'completed_cases': len(rows),
        'expected_cases': config['cases'], 'status': 'PASSED' if error is None else 'STOPPED', 'error': error,
        'rows': rows, 'cumulative_python_broker_usage': cumulative.usage(),
        'elapsed_seconds': time.monotonic()-started, 'python_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'worker_requests': worker.ordinal, 'worker_stopped': worker.stopped,
        'durable_python_receipts': durable.records,
        'source_loader_preflight': getattr(sys, '_radio_native_v2_source_policy_preflight', None),
        'native_case_execution': False, 'public_mutations': 0, 'rng_draws': 0, 'telescope_reads': 0,
        'native_case_reservations': 0, 'automatic_retry': False, **{key: False for key in DISABLED}}
    _write(Path(config['fixture_root'])/'python-result.json', canonical(result))
    return result


def _rss_family(root):
    # This execution profile exposes global /proc PIDs but omits each task's
    # children file. Reconstruct the family from the exposed PPid fields.
    process_rows = {}
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit():
            continue
        try:
            lines = (directory/'status').read_text().splitlines()
            fields = {line.split(':', 1)[0]: line.split(':', 1)[1].strip() for line in lines if ':' in line}
            process_rows[int(fields['Pid'])] = {'proc_pid': int(fields['Pid']),
                'parent_proc_pid': int(fields['PPid']),
                'rss_bytes': int(fields.get('VmRSS', '0 kB').split()[0])*1024}
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    rows = []; queue = [root]; seen = set()
    while queue:
        pid = queue.pop()
        if pid in seen:
            continue
        seen.add(pid)
        if pid in process_rows:
            rows.append(process_rows[pid])
            queue.extend(child for child, row in process_rows.items() if row['parent_proc_pid'] == pid)
    return rows


def measure_fixture(prepared_path, output):
    """Supervise independently of Node's event loop and retain failed stages."""
    prepared = json.loads(Path(prepared_path).read_bytes())
    script = Path(prepared['code_root'])/'scripts/radio_native_v2_local_transport_fixture.js'
    output_log = Path(prepared['fixture_root'])/'node-stdout.log'
    error_log = Path(prepared['fixture_root'])/'node-stderr.log'
    peak = 0; peak_rows = []; samples = 0
    with output_log.open('xb') as out, error_log.open('xb') as err:
        child = subprocess.Popen([prepared['node'], str(script), str(Path(prepared_path).absolute())], stdout=out, stderr=err)
        root_pid = None; started = time.monotonic()
        while child.poll() is None:
            if root_pid is None and output_log.stat().st_size:
                try:
                    root_pid = json.loads(output_log.read_text().splitlines()[0])['proc_pid']
                except (ValueError, KeyError, IndexError):
                    pass
            if root_pid is not None:
                rows = _rss_family(root_pid); measured = sum(row['rss_bytes'] for row in rows); samples += 1
                if measured > peak:
                    peak = measured; peak_rows = rows
            if time.monotonic()-started > 180:
                child.kill(); break
            time.sleep(.01)
        child.wait()
    destination = Path(prepared['fixture_root'])/'node-result.json'
    result = json.loads(destination.read_bytes()) if destination.exists() else {
        'schema': SCHEMA, 'status': 'STOPPED', 'error': error_log.read_text()[-4000:], 'completed_cases': 0}
    result['independent_process_family_measurement'] = {
        'sample_interval_ms': 10, 'samples': samples, 'root_proc_pid': root_pid,
        'parent_resolution': 'GLOBAL_PROC_STATUS_PPID_SCAN',
        'peak_rss_bytes': peak, 'peak_processes': peak_rows,
        'parent_sampler_included': False, 'node_python_helpers_git_included': True,
        'within_512_mib': peak <= 512*1024**2 if samples else False,
        'sampling_can_miss_short_lived_peaks': True,
    }
    result['source_freeze_sha256'] = prepared['freeze_sha256']
    result['source_code_sha256'] = hashlib.sha256(script.read_bytes()).hexdigest()
    _write(Path(output), canonical(result))
    return result


def main():
    # Operational source launcher calls main() with its own immutable argv.
    policy = getattr(sys, '_radio_native_v2_source_policy_preflight', None)
    if policy is not None:
        config_path = Path(__file__).resolve().parents[1]/'fixture-worker-config.json'
        raw_config = config_path.read_bytes()
        freeze = json.loads(Path(sys.argv[-3]).read_bytes())
        if hashlib.sha256(raw_config).hexdigest() != freeze['input_sha256s']['fixture-worker-config.json']:
            raise ValueError('Pinned closed fixture input metadata differs')
        config = json.loads(raw_config)
        print(canonical(publisher_worker(config)).decode(), flush=True)
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare'); parser.add_argument('--worker')
    parser.add_argument('--measure'); parser.add_argument('--output')
    parser.add_argument('--source-bytes', type=int, default=broker.MAX_SOURCE_BYTES)
    parser.add_argument('--cases', type=int, default=2)
    args = parser.parse_args()
    if args.prepare:
        print(canonical(prepare_fixture(args.prepare, source_bytes=args.source_bytes, cases=args.cases)).decode())
    elif args.worker:
        print(canonical(publisher_worker(json.loads(Path(args.worker).read_bytes()))).decode())
    elif args.measure and args.output:
        result = measure_fixture(args.measure, args.output)
        print(canonical({'status': result['status'], 'completed_cases': result['completed_cases'],
                         'output': args.output, 'aggregate_peak_rss_bytes': result['independent_process_family_measurement']['peak_rss_bytes']}).decode())
    else:
        parser.error('--prepare or --worker required')


if __name__ == '__main__':
    main()
