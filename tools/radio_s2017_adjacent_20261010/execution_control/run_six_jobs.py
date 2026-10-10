"""One-shot control for six frozen jobs; no arithmetic or source-value reads.

Waves are fixed native170/native172 batch01, then02, then03. Each original
driver owns its resource/source/job/two-slot kernel locks. This controller
requires root GO after durable RAW save and sidecar release; any failed job
prevents later waves and is never retried. All logs stay outside RAW sources.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

BASE = Path('analysis/s2017_next_native')
CONTROL = Path('analysis/s2017_next_native_execution')
FREEZE = '2ba6ee3497abf3d24e5190df8630133f8a04bcb0'
DRIVER_SHA = '3c23e8020ee32c5c662922d16fe3517315364eccb59514b9e678e6d248b519e6'
PREFLIGHT_SHA = '0e4b8fce10d1d3749eeeec850dcf39c59b5a8ebc80f798c40b2845b0fc383f23'
COMPLETE = 'COMPLETE_S2017_ADJACENT_NATIVE_SAFE_INTERIOR_JOB_EXPLORATORY_ONLY'
WAVES = (
    (('native170_batch01', '4b73cedea7872b70cb098e374f954a04e77674a6d7d9cea3ae3be0a8c6d84345'),
     ('native172_batch01', '577d90d832d498dfb6b4addab8d490e4b826e6129ec5a7a4c4415ead2ff63a2d')),
    (('native170_batch02', '970a0505c96cecc2f496deb05425018db98b73cc794e36aff754e8d493c342fa'),
     ('native172_batch02', '1c534e3ea486b4503494fa1e2fcf4ab915661471e8c07cd490fb88c64f4b992f')),
    (('native170_batch03', '52666368598e29fee75a0135cd051f6443df8be9940c499e3416faa9a07a9253'),
     ('native172_batch03', 'e912a94bb307e07d610c3d52164dbab0138301501cf0791ec3ac4fcd8f29f8c1')))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(path)


def relative(root, name):
    p = Path(name)
    require(not p.is_absolute() and '..' not in p.parts, 'Confined root-relative proof path required')
    result = (root / p).resolve()
    require(result.is_relative_to(root), 'Proof path outside workspace')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--freeze-commit', required=True)
    parser.add_argument('--raw-package-receipt-sha256', required=True)
    parser.add_argument('--raw-release-receipt-path', required=True)
    parser.add_argument('--raw-release-receipt-sha256', required=True)
    parser.add_argument('--root-go-after-raw-save-and-sidecar-release', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    require(args.freeze_commit == FREEZE, 'Exact independently read-back science freeze required')
    require(args.root_go_after_raw_save_and_sidecar_release, 'Root actual durable RAW/release review and science GO required')
    for value in (args.raw_package_receipt_sha256, args.raw_release_receipt_sha256):
        require(re.fullmatch('[0-9a-f]{64}', value), 'Actual root-reviewed proof SHA required')
    driver = root / BASE / 'search/driver.py'
    preflight = root / CONTROL / 'preflight/SIX_CHECK_ONLY_RECEIPT.json'
    require(digest(driver) == DRIVER_SHA and digest(preflight) == PREFLIGHT_SHA, 'Frozen driver/admission bytes changed')
    require(json.loads(preflight.read_bytes())['status'] == 'PASS_ALL_SIX_CHECK_ONLY_NO_VALUES_NO_HTTP', 'All6 actual freeze metadata admissions required')
    raw_receipt_path = root / BASE / 'delivery/RAW_PACKAGE_RECEIPT.json'
    require(digest(raw_receipt_path) == args.raw_package_receipt_sha256, 'Root-reviewed RAW package receipt changed')
    raw = json.loads(raw_receipt_path.read_bytes())
    require(raw['status'] == 'PASS_ARCHIVE_CRC_AND_ALL_MEMBER_SHA256' and raw['kind'] == 'RAW'
        and raw['public_freeze_commit'] == FREEZE, 'Exact completed RAW archive admission required')
    release_path = relative(root, args.raw_release_receipt_path)
    require(digest(release_path) == args.raw_release_receipt_sha256, 'Root-reviewed durable RAW/sidecar-release proof changed')
    # Root owns durable-save and deletion decisions; its exact reviewed proof
    # is recorded here without reinterpreting connector-specific fields.
    json.loads(release_path.read_bytes())
    env = dict(os.environ)
    env['PYTHONPATH'] = str(root / 'analysis/deps')
    python = env['CODEX_PRIMARY_RUNTIME_PYTHON']
    for wave in WAVES:
        for job_id, scope_sha in wave:
            scope_path = root / BASE / 'search/scopes' / (job_id + '.json')
            require(digest(scope_path) == scope_sha, 'Exact reviewed scope changed: ' + job_id)
            require(not (root / BASE / 'results/search' / job_id).exists(), 'No existing job may be retried: ' + job_id)
    lock = (root / CONTROL / 'ORCHESTRATION_ACTIVE_FLOCK.lock').open('a+b')
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    out = root / CONTROL / 'actual_run'
    out.mkdir(exist_ok=False)
    receipt = {'schema': 'SETI_S2017_ADJACENT_SIX_ONE_SHOT_EXECUTION_CONTROL_V1',
        'status': 'IN_PROGRESS', 'started_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'public_freeze_commit': FREEZE, 'driver_sha256': DRIVER_SHA,
        'controller_sha256': digest(__file__), 'metadata_admission_sha256': PREFLIGHT_SHA,
        'RAW_package_receipt_sha256': args.raw_package_receipt_sha256,
        'root_RAW_save_and_release_proof_path': args.raw_release_receipt_path,
        'root_RAW_save_and_release_proof_sha256': args.raw_release_receipt_sha256,
        'waves': [[job for job, sha in wave] for wave in WAVES],
        'simultaneous_jobs_max': 2, 'retry_resume_rerun_authorized': False,
        'HTTP_requests': 0, 'controller_H5_NPZ_values_read': False, 'jobs': []}
    active, logs = [], []
    try:
        save(out / 'ORCHESTRATION_RECEIPT.json', receipt)
        for wave_index, wave in enumerate(WAVES, 1):
            active, logs = [], []
            for job_id, scope_sha in wave:
                require(digest(driver) == DRIVER_SHA, 'Frozen driver changed before launch')
                scope_path = root / BASE / 'search/scopes' / (job_id + '.json')
                require(digest(scope_path) == scope_sha, 'Frozen scope changed before launch')
                log_path = out / (job_id + '.log')
                log = log_path.open('xb')
                logs.append(log)
                command = [python, str(driver), '--root', str(root), '--scope', str(scope_path),
                    '--expected-scope-sha256', scope_sha, '--freeze-commit', FREEZE, '--root-go-after-review']
                job = {'job_id': job_id, 'wave': wave_index, 'scope_sha256': scope_sha,
                    'command': command, 'log_path': log_path.relative_to(root).as_posix(),
                    'status': 'STARTED_ONCE', 'started_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat()}
                receipt['jobs'].append(job)
                process = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
                job['process_id'] = process.pid
                active.append((job, process, log_path))
                save(out / 'ORCHESTRATION_RECEIPT.json', receipt)
                print('STARTED_ONCE', job_id, process.pid, flush=True)
            last_progress = time.monotonic() - 30
            while any(process.poll() is None for job, process, log_path in active):
                if time.monotonic() - last_progress >= 30:
                    progress = []
                    for job, process, log_path in active:
                        checkpoint = root / BASE / 'results/search' / job['job_id'] / 'DRIFT_CHECKPOINT.json'
                        counts = json.loads(checkpoint.read_bytes()) if checkpoint.exists() else {}
                        progress.append({'job_id': job['job_id'], 'completed_ON_maps': counts.get('completed_ON_maps', 0),
                            'expected_ON_maps': counts.get('expected_ON_maps', 255 if wave_index < 3 else 252),
                            'process_exit_code': process.poll()})
                    receipt['last_saved_checkpoint_progress'] = progress
                    save(out / 'ORCHESTRATION_RECEIPT.json', receipt)
                    print('SAVED_CHECKPOINT_PROGRESS', json.dumps(progress), flush=True)
                    last_progress = time.monotonic()
                time.sleep(1)
            for log in logs:
                log.flush()
                os.fsync(log.fileno())
                log.close()
            logs = []
            valid = True
            for job, process, log_path in active:
                job['exit_code'] = process.returncode
                job['log_sha256'] = digest(log_path)
                result_path = root / BASE / 'results/search' / job['job_id'] / 'EXECUTION_RECEIPT.json'
                if result_path.exists():
                    result = json.loads(result_path.read_bytes())
                    job.update(status=result['status'], actual_receipt_path=result_path.relative_to(root).as_posix(),
                        actual_receipt_sha256=digest(result_path),
                        completed_ON_maps=result.get('search_summary', {}).get('completed_ON_maps', 0),
                        process_CPU_seconds=result.get('process_CPU_seconds_including_imports'),
                        wall_seconds=result.get('wall_seconds_including_imports'), peak_RSS_bytes=result.get('peak_RSS_bytes'))
                    ok = process.returncode == 0 and result['status'] == COMPLETE
                else:
                    job['status'] = 'NO_COMPLETED_JOB_RECEIPT_PRESERVE_LOG'
                    ok = False
                valid = valid and ok
                print('TERMINAL_JOB_RECEIPT', json.dumps(job), flush=True)
            save(out / 'ORCHESTRATION_RECEIPT.json', receipt)
            require(valid, 'A wave failed or is incomplete; later waves held, no retries')
        receipt.update(status='COMPLETE_ALL_SIX_ONCE_EXACT_RECEIPTS_NO_RETRY',
            completed_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            completed_ON_maps=sum(job['completed_ON_maps'] for job in receipt['jobs']),
            total_measured_job_CPU_seconds=sum(job['process_CPU_seconds'] for job in receipt['jobs']))
        require(receipt['completed_ON_maps'] == 1524, 'All1524 saved maps required')
        save(out / 'ORCHESTRATION_RECEIPT.json', receipt)
        print(json.dumps({'status': receipt['status'], 'completed_ON_maps': receipt['completed_ON_maps']}), flush=True)
    except BaseException as error:
        # Already started jobs may complete under their original frozen caps;
        # wait for them once, preserve their logs, and never launch a replacement.
        for job, process, log_path in active:
            if process.poll() is None:
                process.wait()
        receipt.update(status='INCOMPLETE_CONTROLLER_PRESERVE_STARTED_JOBS_NO_RETRY',
            error_type=type(error).__name__, error=str(error))
        save(out / 'ORCHESTRATION_RECEIPT.json', receipt)
        raise
    finally:
        for log in logs:
            if not log.closed:
                log.close()
        lock.close()


if __name__ == '__main__':
    main()
