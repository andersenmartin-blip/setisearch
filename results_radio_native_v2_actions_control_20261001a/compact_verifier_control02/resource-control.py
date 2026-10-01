#!/usr/bin/env python3
"""One fresh, read-only full03 receipt replay; no native case or retry."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
TRACE = Path('/workspace/scratch/f3b7c4d77b54/qualified-courier-offline-full03/caller-result.json')
CALLER_RSS = TRACE.parent / 'independent-rss-final.json'
RSS_CAP = 512 * 1024**2
STORAGE_CAP = 192 * 1024**2


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def write(path, value):
    raw = value if isinstance(value, bytes) else canonical(value) + b'\n'
    with Path(path).open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def pin(path):
    digest = hashlib.sha256(); count = 0
    with Path(path).open('rb') as stream:
        for raw in iter(lambda: stream.read(65536), b''):
            count += len(raw); digest.update(raw)
    return {'bytes': count, 'sha256': digest.hexdigest()}


def memory(pid):
    rows = {}
    for line in (Path('/proc') / str(pid) / 'status').read_text().splitlines():
        if ':' in line:
            key, value = line.split(':', 1); rows[key] = value.strip()
    return {'at_epoch_ms': time.time_ns() // 1000000,
        'rss_bytes': int(rows.get('VmRSS', '0 kB').split()[0]) * 1024,
        'kernel_vm_hwm_bytes': int(rows.get('VmHWM', '0 kB').split()[0]) * 1024}


def worker():
    write(ROOT / 'worker-identity.json', {'procfs_pid': int(os.readlink('/proc/self')),
        'namespace_pid': os.getpid(), 'started_at_epoch_ms': time.time_ns() // 1000000})
    script = ROOT / 'frozen-code/scripts/radio_native_v2_compact_run_verifier.py'
    spec = importlib.util.spec_from_file_location('frozen_compact_verifier', script)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    verifier = module.CompactRunVerifier(ROOT / 'compact-receipt', json.loads((ROOT / 'input-plan.json').read_bytes()))
    verifier.append(0); receipt = verifier.finish()
    write(ROOT / 'worker-result.json', {'schema': 'radio-native-v2-compact-verifier-resource-control-worker-v1',
        'receipt_status': receipt['status'], 'case_count': receipt['case_count'],
        'source_pin': receipt['cases'][0]['sha256'], 'calls': receipt['calls'],
        'request_bytes': receipt['request_bytes'], 'response_bytes': receipt['response_bytes'],
        'original_shared_case_elapsed_seconds': receipt['elapsed_seconds'],
        'verification_elapsed_seconds': receipt['verification_elapsed_seconds'],
        'python_ru_maxrss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'execution_authorized': False, 'reservation_authorized': False,
        'scientific_execution_authorized': False, 'native_case_executions': 0,
        'rng_draws': 0, 'telescope_reads': 0})


def main():
    if len(sys.argv) == 2 and sys.argv[1] == '--worker':
        worker(); return
    if len(sys.argv) != 1 or set(p.name for p in ROOT.iterdir()) != {'resource-control.py'}:
        raise RuntimeError('Fresh control scope required; no retry or resume')
    started = time.monotonic(); source_pin = pin(TRACE); rss_pin = pin(CALLER_RSS)
    caller_peak = json.loads(CALLER_RSS.read_bytes())['client_peak_rss_bytes']
    files = ('scripts/radio_native_v2_compact_run_verifier.py', 'src/seti_repeater/__init__.py',
        'src/seti_repeater/empty_null_radio.py', 'src/seti_repeater/native_v2_transport_contract_radio.py')
    code = {}
    for relative in files:
        source = REPO / relative; destination = ROOT / 'frozen-code' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes(); write(destination, raw); code[relative] = pin(destination)
    plan = {'schema': 'radio-native-v2-compact-retained-run-plan-v1',
        'run_id': 'compact-verifier-retained-full03-control02', 'cases': [{
        'ordinal': 0, 'source_case_id': 'qualified-courier-offline-full03/original-case00',
        'source_path': str(TRACE), **source_pin, 'client_peak_rss_bytes': caller_peak,
        'other_host_receipt_bytes': 0, 'other_host_receipt_allocated_bytes': 0}]}
    write(ROOT / 'input-plan.json', plan)
    write(ROOT / 'prospective-pins.json', {'schema': 'radio-native-v2-compact-verifier-resource-control-pins-v1',
        'source': {'path': str(TRACE), **source_pin}, 'original_rss': {'path': str(CALLER_RSS), **rss_pin},
        'code': code, 'control': pin(__file__), 'python': {'resolved': str(Path(sys.executable).resolve()),
        'version': sys.version, **pin(Path(sys.executable).resolve())}, 'rss_cap_bytes': RSS_CAP,
        'receipt_storage_cap_bytes': STORAGE_CAP, 'seconds_cap': 600,
        'new_verification_namespace_only': True, 'historical_source_scope_unchanged': True,
        'native_case_executions': 0, 'rng_draws': 0, 'telescope_reads': 0})
    stdout = (ROOT / 'worker-stdout.log').open('xb'); stderr = (ROOT / 'worker-stderr.log').open('xb')
    observed_start = time.time_ns() // 1000000
    child = subprocess.Popen([sys.executable, '-I', '-S', '-B', str(Path(__file__).resolve()), '--worker'],
        stdout=stdout, stderr=stderr, env={'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'})
    samples = []; proc_pid = None; timeout = False
    try:
        while True:
            identity = ROOT / 'worker-identity.json'
            if proc_pid is None and identity.exists():
                try: proc_pid = json.loads(identity.read_bytes())['procfs_pid']
                except json.JSONDecodeError: pass
            if proc_pid is not None:
                try: samples.append(memory(proc_pid))
                except (FileNotFoundError, ProcessLookupError): pass
            waited_pid, status, usage = os.wait4(child.pid, os.WNOHANG)
            if waited_pid:
                child.returncode = os.waitstatus_to_exitcode(status); break
            if time.monotonic() - started > 600 and not timeout:
                timeout = True; child.kill()
            time.sleep(0.005)
    finally:
        stdout.close(); stderr.close()
    observed_end = time.time_ns() // 1000000
    peak = max([usage.ru_maxrss * 1024] + [max(row['rss_bytes'], row['kernel_vm_hwm_bytes']) for row in samples])
    write(ROOT / 'independent-rss-observation.json', {'schema': 'radio-native-v2-compact-verifier-parent-rss-v1',
        'observer_source': 'independent_parent_procfs_and_kernel_wait4',
        'observer_procfs_pid': int(os.readlink('/proc/self')), 'worker_procfs_pid': proc_pid,
        'interval_start_epoch_ms': observed_start, 'interval_end_epoch_ms': observed_end,
        'sample_count': len(samples), 'wait4_ru_maxrss_bytes': usage.ru_maxrss * 1024,
        'independent_peak_rss_bytes': peak, 'includes_entire_child_lifetime': True,
        'exit_code': child.returncode, 'samples': samples})
    result = json.loads((ROOT / 'worker-result.json').read_bytes()) if (ROOT / 'worker-result.json').exists() else None
    rows = [{'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size,
        'allocated_bytes': path.stat().st_blocks * 512} for path in sorted(ROOT.rglob('*')) if path.is_file()]
    logical = sum(row['bytes'] for row in rows) + TRACE.stat().st_size + CALLER_RSS.stat().st_size
    allocated = sum(row['allocated_bytes'] for row in rows) + TRACE.stat().st_blocks * 512 + CALLER_RSS.stat().st_blocks * 512
    failures = []
    if not 0 < peak <= RSS_CAP: failures.append('Original 512MiB verifier process cap failed')
    if timeout or (observed_end - observed_start) / 1000 > 600: failures.append('Original 600-second control interval failed')
    if logical > STORAGE_CAP or allocated > STORAGE_CAP: failures.append('Original 192MiB input-inclusive control storage cap failed')
    if child.returncode != 0 or result is None: failures.append('Complete compact verifier worker failed')
    if pin(TRACE) != source_pin or pin(CALLER_RSS) != rss_pin: failures.append('Historical read-only input changed')
    if any(pin(REPO / relative) != wanted for relative, wanted in code.items()): failures.append('Original source code changed during control')
    summary = {'schema': 'radio-native-v2-compact-verifier-resource-control-v1',
        'status': 'PASSED' if not failures else 'CLOSED_FAILED', 'failures': failures,
        'mode': 'ONE_RETAINED_OFFLINE_CASE_VERIFICATION_ONLY', 'source_pin': source_pin,
        'independent_peak_rss_bytes': peak, 'wait4_ru_maxrss_bytes': usage.ru_maxrss * 1024,
        'observer_self_ru_maxrss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'child_interval_seconds': (observed_end - observed_start) / 1000,
        'whole_control_seconds_before_summary': time.monotonic() - started,
        'input_inclusive_storage_before_summary': {'logical_bytes': logical, 'allocated_bytes': allocated,
            'files': rows, 'summary_and_storage_audit_itself_excluded': True}, 'worker_result': result,
        'eight_case_resources_qualified': False, 'native_case_executions': 0,
        'historical_case_retried': False, 'source_case_identity_independently_bound_to_native_runner': False,
        'other_host_storage_independently_verified': False, 'scientific_runtime_closure_frozen': False,
        'execution_authorized': False, 'reservation_authorized': False,
        'scientific_execution_authorized': False, 'rng_draws': 0, 'telescope_reads': 0,
        'automatic_retry': False, 'original_limits': {'rss_bytes': RSS_CAP, 'seconds': 600,
            'case_receipt_storage_bytes': STORAGE_CAP}}
    write(ROOT / 'measured-summary.json', summary)
    rows = [{'path': str(path.relative_to(ROOT)), **pin(path), 'allocated_bytes': path.stat().st_blocks * 512}
        for path in sorted(ROOT.rglob('*')) if path.is_file()]
    write(ROOT / 'storage-inventory.json', {'files': rows, 'inventory_itself_excluded': True,
        'control_logical_bytes': sum(row['bytes'] for row in rows),
        'control_allocated_bytes': sum(row['allocated_bytes'] for row in rows),
        'historical_inputs_retained_at_original_paths': True})
    print(json.dumps({'status': summary['status'], 'independent_peak_rss_bytes': peak,
        'wait4_ru_maxrss_bytes': usage.ru_maxrss * 1024, 'child_interval_seconds': summary['child_interval_seconds'],
        'input_inclusive_logical_storage': logical, 'failures': failures}, sort_keys=True))


if __name__ == '__main__':
    main()
