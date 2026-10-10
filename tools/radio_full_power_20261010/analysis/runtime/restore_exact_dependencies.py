#!/usr/bin/env python3
"""One-shot dependency-only restoration; no telescope files are accessed."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'analysis/runtime'
WHEELS = OUT / 'wheels'
TARGET = ROOT / 'analysis/deps'
SOURCE = ROOT / 'sources/SETI_GAP_STATIC_CONTEXT_2026-10-10/results/radio_gap_static_context_20261010/ENVIRONMENT_RESTORATION.json'
RECEIPT = OUT / 'EXACT_DEPENDENCY_RESTORATION.json'
WHEELS.mkdir(parents=True, exist_ok=True)
started = time.monotonic()
receipt = {
    'status': 'STARTED', 'started_UTC': dt.datetime.now(dt.timezone.utc).isoformat(),
    'source_receipt': str(SOURCE), 'Python_executable': sys.executable,
    'workspace_target': str(TARGET), 'wheel_GET_requests': 0,
    'dependency_wheel_body_bytes': 0, 'wheel_downloads': [],
    'retry_performed': False, 'alternate_versions_or_routes': False,
    'new_telescope_HTTP_requests': 0, 'new_telescope_power_bytes': 0,
    'HDF5_or_NPZ_values_opened': False,
    'per_request_timeout_s': 30, 'download_total_deadline_s': 120,
    'scope': 'Exact pinned dependency-only restoration into workspace, offline no-dependency install; no telescope reads.'
}

def save():
    receipt['wall_s'] = time.monotonic() - started
    receipt['finished_UTC'] = dt.datetime.now(dt.timezone.utc).isoformat()
    RECEIPT.write_text(json.dumps(receipt, indent=2) + '\n')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('Redirect refused; alternate routes are not authorized')

try:
    import numpy
    baseline = {'version': numpy.__version__, 'module_path': numpy.__file__}
    receipt['unchanged_NumPy_before'] = baseline
    receipt['Python'] = sys.version.split()[0]
    if baseline['version'] != '2.3.5' or sys.version_info[:2] != (3, 12):
        raise RuntimeError('Required baseline is Python 3.12 and NumPy 2.3.5')
    previous = json.loads(SOURCE.read_text())
    receipt['source_receipt_sha256'] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    opener = urllib.request.build_opener(NoRedirect)
    wheel_paths = []
    for pinned in previous['wheel_downloads']:
        entry = {key: pinned[key] for key in ('name', 'url', 'expected_bytes', 'expected_sha256')}
        entry.update({'GET_requests': 1, 'received_body_bytes': 0, 'SHA256_verified_before_install': False})
        receipt['wheel_downloads'].append(entry)
        receipt['wheel_GET_requests'] += 1
        path = WHEELS / entry['name']
        if path.exists():
            raise RuntimeError('Destination wheel already exists; refusing duplicate download')
        begin = time.monotonic()
        req = urllib.request.Request(entry['url'], headers={'User-Agent': 'SETI-exact-dependency-restoration/2026-10-10'})
        with opener.open(req, timeout=30) as response, path.open('xb') as output:
            entry['status'] = response.status
            entry['final_url'] = response.geturl()
            entry['headers'] = dict(response.headers)
            if response.status != 200 or response.geturl() != entry['url']:
                raise RuntimeError('Unexpected HTTP status or final URL')
            digest = hashlib.sha256()
            while True:
                if time.monotonic() - started > 120:
                    raise TimeoutError('Download total deadline exceeded')
                chunk = response.read(min(1024 * 1024, entry['expected_bytes'] + 1 - entry['received_body_bytes']))
                if not chunk:
                    break
                entry['received_body_bytes'] += len(chunk)
                receipt['dependency_wheel_body_bytes'] += len(chunk)
                if entry['received_body_bytes'] > entry['expected_bytes']:
                    raise RuntimeError('Wheel body exceeds exact expected size')
                output.write(chunk)
                digest.update(chunk)
        entry['received_sha256'] = digest.hexdigest()
        entry['wall_s'] = time.monotonic() - begin
        entry['path'] = str(path)
        if entry['received_body_bytes'] != entry['expected_bytes'] or entry['received_sha256'] != entry['expected_sha256']:
            raise RuntimeError('Wheel size or SHA256 mismatch')
        entry['SHA256_verified_before_install'] = True
        wheel_paths.append(str(path))
        save()
    command = [sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', '--no-index', '--no-deps', '--no-cache-dir', '--no-compile', '--target', str(TARGET), *wheel_paths]
    receipt['pip_command_argv'] = command
    installed = subprocess.run(command, capture_output=True, text=True, timeout=120)
    (OUT / 'exact_dependency_pip_install.log').write_text(installed.stdout + installed.stderr)
    receipt['pip_returncode'] = installed.returncode
    installed.check_returncode()
    check = "import json,numpy,h5py,hdf5plugin,importlib.metadata; print(json.dumps({'numpy':numpy.__version__,'numpy_path':numpy.__file__,'h5py':h5py.__version__,'h5py_path':h5py.__file__,'HDF5':h5py.version.hdf5_version,'hdf5plugin':importlib.metadata.version('hdf5plugin'),'hdf5plugin_path':hdf5plugin.__file__}))"
    environment = os.environ.copy()
    environment['PYTHONPATH'] = str(TARGET)
    verified = subprocess.run([sys.executable, '-c', check], capture_output=True, text=True, env=environment, timeout=30)
    (OUT / 'exact_dependency_version_verification.log').write_text(verified.stdout + verified.stderr)
    receipt['version_verification_returncode'] = verified.returncode
    verified.check_returncode()
    versions = json.loads(verified.stdout)
    receipt['versions_verified'] = versions
    if (versions['numpy'], versions['h5py'], versions['hdf5plugin']) != ('2.3.5', '3.15.1', '7.1.0') or versions['numpy_path'] != baseline['module_path']:
        raise RuntimeError('Post-install exact environment verification mismatch')
    receipt['NumPy_original_version_and_module_path_preserved'] = True
    receipt['status'] = 'PASS_EXACT_PREVIOUS_STANDARD_ENVIRONMENT_RESTORED'
except Exception as error:
    receipt['status'] = 'STOP_RESTORATION_FAILED_NO_RETRY'
    receipt['error_type'] = type(error).__name__
    receipt['error'] = str(error)
    save()
    print(json.dumps({'status':receipt['status'], 'error':str(error), 'receipt':str(RECEIPT)}))
    sys.exit(1)
save()
print(json.dumps({'status':receipt['status'], 'versions':receipt['versions_verified'], 'receipt':str(RECEIPT)}))
