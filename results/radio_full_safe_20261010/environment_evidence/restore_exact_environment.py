"""Restore two previously pinned wheels without touching telescope values."""
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import resource
import signal
import subprocess
import sys
import time
import urllib.request

START = time.monotonic()
BASE = Path('/workspace/scratch/a8d1e29996d0')
WORK = BASE / 'seti_fullpower_work'
PRIOR_EVIDENCE = BASE / 'setisearch_fullpower/results/radio_gap_drift_20261010/environment_evidence'
EVIDENCE = BASE / 'setisearch_fullpower/results/radio_full_safe_20261010/environment_evidence'
WHEELS = WORK / 'wheels'
TARGET = WORK / 'deps'
OUT = EVIDENCE.parent
LIMITS = {'CPU_s': 15, 'wall_s': 1800, 'memory_bytes': 4 * 1024**3}

def deadline(signum, frame):
    raise TimeoutError('Exact environment restoration reached frozen wall/CPU cap')

signal.signal(signal.SIGALRM, deadline)
signal.signal(signal.SIGXCPU, deadline)
signal.alarm(LIMITS['wall_s'])
resource.setrlimit(resource.RLIMIT_CPU, (LIMITS['CPU_s'], LIMITS['CPU_s'] + 1))
resource.setrlimit(resource.RLIMIT_AS, (LIMITS['memory_bytes'], LIMITS['memory_bytes']))

EXPECTED = (
    ('h5py_3.15.1', 'h5py-3.15.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl',
     5109965, '25c8843fec43b2cc368aa15afa1cdf83fc5e17b1c4e10cd3771ef6c39b72e5ce'),
    ('hdf5plugin_7.1.0', 'hdf5plugin-7.1.0-py3-none-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl',
     46397731, '9d4cf36434819fae53e4da432f0287ebaeb02386ab97b73d261092efbab12247'),
)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Unexpected redirect; no new request permitted')

def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')

def cpu_components():
    own = resource.getrusage(resource.RUSAGE_SELF)
    kids = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {'wrapper_CPU_s': own.ru_utime + own.ru_stime,
            'subprocess_children_CPU_s': kids.ru_utime + kids.ru_stime,
            'sum_measured_local_process_components_CPU_s': own.ru_utime + own.ru_stime + kids.ru_utime + kids.ru_stime,
            'wrapper_peak_RSS_bytes': own.ru_maxrss * 1024,
            'largest_child_peak_RSS_bytes': kids.ru_maxrss * 1024}


def remaining_child_CPU_limits():
    # This is only a tighter resource bound on the unchanged subprocess route.
    remaining = LIMITS['CPU_s'] - cpu_components()['sum_measured_local_process_components_CPU_s']
    child_limit = int(remaining - 1.0)
    assert child_limit >= 1, 'Insufficient remaining CPU for next unchanged step; no retry'
    def set_child_limit():
        resource.setrlimit(resource.RLIMIT_CPU, (child_limit, child_limit))
    return set_child_limit

receipt = {'status': 'STARTED_EXACT_PREVIOUS_ENVIRONMENT_RESTORATION',
           'started_UTC': datetime.now(timezone.utc).isoformat(),
           'reservation_commit': '24f1a3a9d369e58464046dd1c51130b62fb75c57',
           'workspace_target': str(TARGET), 'limits': LIMITS,
           'new_telescope_HTTP_requests': 0, 'new_telescope_power_bytes': 0,
           'HDF5_or_NPZ_values_opened': False, 'alternate_versions_or_routes': False,
           'wheel_GET_requests': 0, 'dependency_wheel_body_bytes': 0,
           'wheel_downloads': [], 'retry_performed': False,
           'new_metadata_GET_requests': 0, 'new_wheel_HEAD_requests': 0,
           'previous_restoration_script_sha256': '4692846ff18c90e1ec95f78e2199ce05de9cf1e549e0ddf7e4f3895ba4685573',
           'original_standard_restoration_script_sha256': '9a16aece4fab96886c6e56ff818e3594ecd6e2c9d6ff1b11da22d96766ec813a',
           'budget_definition': 'Sum of wrapper and subprocess children CPU; child CPU limits use the remaining budget with a one-second wrapper/finalization margin.'}

def download(item):
    label, name, size, digest = item
    prior = json.loads((PRIOR_EVIDENCE / (label + '_pypi_metadata_receipt.json')).read_text())
    wheel = prior['wheel']
    assert wheel['filename'] == name and wheel['size'] == size and wheel['sha256'] == digest
    assert prior['matches_previous_receipt'] is True
    part = WHEELS / (name + '.part')
    final = WHEELS / name
    assert not part.exists() and not final.exists()
    result = {'name': name, 'url': wheel['url'], 'expected_bytes': size,
              'expected_sha256': digest, 'GET_requests': 0, 'received_body_bytes': 0,
              'SHA256_verified_before_install': False}
    started = time.monotonic()
    sha = hashlib.sha256()
    try:
        req = urllib.request.Request(wheel['url'], method='GET',
                                     headers={'Accept-Encoding': 'identity',
                                              'User-Agent': 'SETI-exact-environment-restoration/1.0'})
        opener = urllib.request.build_opener(NoRedirect)
        result['GET_requests'] = 1
        with opener.open(req, timeout=60) as response:
            result.update(status=response.status, final_url=response.url,
                          headers=dict(response.headers))
            assert response.status == 200 and response.url == wheel['url']
            assert int(response.headers['Content-Length']) == size
            assert response.headers.get('Content-Encoding', 'identity') == 'identity'
            with part.open('xb') as fh:
                while True:
                    body = response.read(min(1024**2, size + 1 - result['received_body_bytes']))
                    if not body:
                        break
                    result['received_body_bytes'] += len(body)
                    assert result['received_body_bytes'] <= size, 'Wheel byte cap exceeded'
                    sha.update(body)
                    fh.write(body)
        result['received_sha256'] = sha.hexdigest()
        assert result['received_body_bytes'] == size and sha.hexdigest() == digest
        part.rename(final)
        result.update(path=str(final), SHA256_verified_before_install=True)
    except BaseException as exc:
        result.update(error_type=type(exc).__name__, error=str(exc))
    result['wall_s'] = time.monotonic() - started
    save(EVIDENCE / (label + '_wheel_GET_receipt.json'), result)
    return result

try:
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    assert not (OUT / 'ENVIRONMENT_RESTORATION.json').exists()
    assert not TARGET.exists() and not WHEELS.exists()
    assert sys.version_info[:2] == (3, 12) and platform.machine() == 'x86_64'
    assert importlib.util.find_spec('pip') is not None, 'Previously standard pip path unavailable'
    import numpy
    assert numpy.__version__ == '2.3.5'
    numpy_path = str(Path(numpy.__file__).resolve())
    receipt['unchanged_NumPy_before'] = {'version': numpy.__version__, 'module_path': numpy_path}
    receipt['Python'] = sys.version.split()[0]
    receipt['Python_executable'] = sys.executable
    WHEELS.mkdir()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        downloads = list(pool.map(download, EXPECTED))
    receipt['wheel_downloads'] = downloads
    receipt['wheel_GET_requests'] = sum(x['GET_requests'] for x in downloads)
    receipt['dependency_wheel_body_bytes'] = sum(x['received_body_bytes'] for x in downloads)
    assert all(x['SHA256_verified_before_install'] for x in downloads), 'A pinned wheel download failed; no installation'
    assert time.monotonic() - START < LIMITS['wall_s']
    install = [sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
               '--no-index', '--no-deps', '--no-cache-dir', '--no-compile',
               '--target', str(TARGET)] + [x['path'] for x in downloads]
    receipt['pip_command_argv'] = install
    pip_cpu_start = cpu_components()['subprocess_children_CPU_s']
    pip_wall_start = time.monotonic()
    pip_result = subprocess.run(install, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, preexec_fn=remaining_child_CPU_limits(),
                                timeout=max(1, LIMITS['wall_s'] - (time.monotonic() - START)))
    (EVIDENCE / 'exact_environment_pip_install.log').write_text(pip_result.stdout)
    receipt['pip_returncode'] = pip_result.returncode
    receipt['pip_wall_s'] = time.monotonic() - pip_wall_start
    receipt['pip_measured_child_CPU_s'] = cpu_components()['subprocess_children_CPU_s'] - pip_cpu_start
    assert pip_result.returncode == 0, 'Pinned pip installation failed; no retry or alternate route'
    env = os.environ.copy()
    env['PYTHONPATH'] = str(TARGET) + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    verification_code = """import json,pathlib,importlib.metadata,numpy,h5py,hdf5plugin
print(json.dumps({'numpy':numpy.__version__,'numpy_path':str(pathlib.Path(numpy.__file__).resolve()),'h5py':h5py.__version__,'h5py_path':str(pathlib.Path(h5py.__file__).resolve()),'HDF5':h5py.version.hdf5_version,'hdf5plugin':importlib.metadata.version('hdf5plugin'),'hdf5plugin_path':str(pathlib.Path(hdf5plugin.__file__).resolve())}))
"""
    version_start = cpu_components()['subprocess_children_CPU_s']
    version_wall = time.monotonic()
    checked = subprocess.run([sys.executable, '-c', verification_code], env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             preexec_fn=remaining_child_CPU_limits(), timeout=max(1, LIMITS['wall_s'] - (time.monotonic() - START)))
    (EVIDENCE / 'exact_environment_version_verification.log').write_text(checked.stdout)
    receipt['version_verification_returncode'] = checked.returncode
    receipt['version_verification_child_CPU_s'] = cpu_components()['subprocess_children_CPU_s'] - version_start
    receipt['version_verification_wall_s'] = time.monotonic() - version_wall
    assert checked.returncode == 0, 'Package-version verification failed; no retry'
    versions = json.loads(checked.stdout.strip())
    assert versions['numpy'] == '2.3.5' and versions['numpy_path'] == numpy_path
    assert versions['h5py'] == '3.15.1' and versions['hdf5plugin'] == '7.1.0'
    assert versions['HDF5'] == '1.14.6'
    assert Path(versions['h5py_path']).is_relative_to(TARGET)
    assert Path(versions['hdf5plugin_path']).is_relative_to(TARGET)
    assert not Path(versions['numpy_path']).is_relative_to(TARGET)
    assert not list(TARGET.glob('numpy*'))
    receipt['versions_verified'] = versions
    receipt['NumPy_original_version_and_module_path_preserved'] = True
    prior = json.loads((PRIOR_EVIDENCE / 'EXACT_ENVIRONMENT_AVAILABILITY_REVIEW.json').read_text())
    receipt['prior_official_index_review_historical_not_repeated'] = {'metadata_GET_requests': prior['public_metadata_GETs'],
                                            'metadata_application_body_bytes': prior['new_metadata_application_body_bytes'],
                                            'wheel_HEAD_requests': prior['wheel_HEAD_requests'],
                                            'wheel_HEAD_body_bytes': 0}
    receipt['status'] = 'PASS_EXACT_PREVIOUS_STANDARD_ENVIRONMENT_RESTORED'
except BaseException as exc:
    receipt.update(status='FAILED_CLOSED_EXACT_ENVIRONMENT_RESTORATION',
                   error_type=type(exc).__name__, error=str(exc))
finally:
    signal.alarm(0)
    receipt.update(cpu_components())
    receipt['wall_s'] = time.monotonic() - START
    if (receipt['sum_measured_local_process_components_CPU_s'] > LIMITS['CPU_s']
            or receipt['wall_s'] > LIMITS['wall_s']
            or max(receipt['wrapper_peak_RSS_bytes'], receipt['largest_child_peak_RSS_bytes']) > LIMITS['memory_bytes']):
        receipt['status'] = 'INCOMPLETE_RESOURCE_LIMIT_NO_RETRY'
    receipt['finished_UTC'] = datetime.now(timezone.utc).isoformat()
    receipt['whole_session_CPU_measured'] = False
    receipt['scope'] = 'Dependency-only restoration: exact published wheel identities and no-dependency workspace installation; no telescope or analytical array reads.'
    receipt['evidence_files'] = []
    for fp in [EVIDENCE / 'restore_exact_environment.py', EVIDENCE / 'exact_environment_pip_install.log',
               EVIDENCE / 'exact_environment_version_verification.log'] + list(EVIDENCE.glob('*wheel_GET_receipt.json')):
        if fp.is_file():
            content = fp.read_bytes()
            receipt['evidence_files'].append({'path': str(fp), 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()})
    OUT.mkdir(parents=True, exist_ok=True)
    save(OUT / 'ENVIRONMENT_RESTORATION.json', receipt)
    print(json.dumps({k: receipt[k] for k in ['status', 'wheel_GET_requests', 'dependency_wheel_body_bytes', 'sum_measured_local_process_components_CPU_s', 'wall_s']}))
    if receipt['status'] != 'PASS_EXACT_PREVIOUS_STANDARD_ENVIRONMENT_RESTORED':
        sys.exit(1)
