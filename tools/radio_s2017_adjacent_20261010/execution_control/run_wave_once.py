"""Exactly one root-authorized paired wave; other waves are never launched."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
from run_six_jobs import BASE, CONTROL, FREEZE, DRIVER_SHA, PREFLIGHT_SHA, COMPLETE, WAVES, digest, require, save, relative

CONTROL_SOURCE_SHA = '9c9ff58d7157a53e079914c58b3f9b57aa2df16844eb57b0b87827d68aff14c7'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--wave', required=True, type=int, choices=(1, 2, 3))
    parser.add_argument('--root-go-receipt-path', required=True)
    parser.add_argument('--root-go-receipt-sha256', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    wave = WAVES[args.wave - 1]
    go_path = relative(root, args.root_go_receipt_path)
    require(digest(go_path) == args.root_go_receipt_sha256, 'Root exact wave GO proof changed')
    go = json.loads(go_path.read_bytes())
    require(go['status'].startswith('GO_') and go['public_freeze_commit'] == FREEZE
        and go['jobs'] == [job for job, sha in wave]
        and go['max_simultaneous_science_jobs'] == 2 and go['memory_per_process_bytes'] == 2147483648
        and go['CPU_cap_each_s'] == 1000 and go['retry_resume_or_rerun_authorized'] is False,
        'Exact root GO for this fixed wave only required')
    driver = root / BASE / 'search/driver.py'
    require(digest(root / CONTROL / 'run_six_jobs.py') == CONTROL_SOURCE_SHA, 'Immutable control constants changed')
    require(digest(driver) == DRIVER_SHA, 'Frozen science driver changed')
    require(digest(root / CONTROL / 'preflight/SIX_CHECK_ONLY_RECEIPT.json') == PREFLIGHT_SHA, 'All6 metadata admission changed')
    for job_id, scope_sha in wave:
        require(digest(root / BASE / 'search/scopes' / (job_id + '.json')) == scope_sha, 'Frozen job scope changed')
        require(not (root / BASE / 'results/search' / job_id).exists(), 'Existing science job may never be retried')
    lock = (root / CONTROL / 'ORCHESTRATION_ACTIVE_FLOCK.lock').open('a+b')
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    out = root / CONTROL / ('actual_wave%d' % args.wave)
    out.mkdir(exist_ok=False)
    receipt = {'schema': 'SETI_S2017_ADJACENT_TWO_JOB_ONE_SHOT_WAVE_CONTROL_V1', 'status': 'IN_PROGRESS',
        'wave': args.wave, 'public_freeze_commit': FREEZE, 'driver_sha256': DRIVER_SHA,
        'controller_sha256': digest(__file__), 'constants_sha256': CONTROL_SOURCE_SHA,
        'root_GO_path': args.root_go_receipt_path, 'root_GO_sha256': args.root_go_receipt_sha256,
        'simultaneous_science_jobs_max': 2, 'other_waves_executed_by_this_control': False,
        'retry_resume_rerun_authorized': False, 'HTTP_requests': 0, 'controller_values_read': False,
        'started_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'jobs': []}
    env = dict(os.environ)
    env['PYTHONPATH'] = str(root / 'analysis/deps')
    python = env['CODEX_PRIMARY_RUNTIME_PYTHON']
    active, logs = [], []
    try:
        save(out / 'ORCHESTRATION_RECEIPT.json', receipt)
        for job_id, scope_sha in wave:
            log_path = out / (job_id + '.log')
            log = log_path.open('xb')
            logs.append(log)
            command = [python, str(driver), '--root', str(root), '--scope',
                str(root / BASE / 'search/scopes' / (job_id + '.json')), '--expected-scope-sha256', scope_sha,
                '--freeze-commit', FREEZE, '--root-go-after-review']
            job = {'job_id': job_id, 'status': 'STARTED_ONCE', 'scope_sha256': scope_sha, 'command': command,
                'log_path': log_path.relative_to(root).as_posix(), 'started_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat()}
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
                        'expected_ON_maps': 255 if args.wave < 3 else 252, 'process_exit_code': process.poll()})
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
            job.update(exit_code=process.returncode, log_sha256=digest(log_path))
            path = root / BASE / 'results/search' / job['job_id'] / 'EXECUTION_RECEIPT.json'
            if path.exists():
                result = json.loads(path.read_bytes())
                job.update(status=result['status'], actual_receipt_path=path.relative_to(root).as_posix(), actual_receipt_sha256=digest(path),
                    completed_ON_maps=result.get('search_summary', {}).get('completed_ON_maps', 0),
                    process_CPU_seconds=result.get('process_CPU_seconds_including_imports'),
                    wall_seconds=result.get('wall_seconds_including_imports'), peak_RSS_bytes=result.get('peak_RSS_bytes'))
                ok = process.returncode == 0 and result['status'] == COMPLETE
            else:
                job['status'] = 'NO_COMPLETED_JOB_RECEIPT_PRESERVE_LOG'
                ok = False
            valid = valid and ok
            print('TERMINAL_JOB_RECEIPT', json.dumps(job), flush=True)
        require(valid, 'Failed or incomplete wave preserved; no retry or other wave launch')
        receipt.update(status='COMPLETE_TWO_ROOT_AUTHORIZED_JOBS_ONCE_NO_RETRY',
            completed_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            completed_ON_maps=sum(job['completed_ON_maps'] for job in receipt['jobs']))
        save(out / 'ORCHESTRATION_RECEIPT.json', receipt)
        print(json.dumps({'status': receipt['status'], 'wave': args.wave, 'completed_ON_maps': receipt['completed_ON_maps']}), flush=True)
    except BaseException as error:
        # Poll existing children only; no replacement launch is possible.
        while any(process.poll() is None for job, process, log_path in active):
            time.sleep(1)
        receipt.update(status='INCOMPLETE_WAVE_PRESERVE_STARTED_JOBS_NO_RETRY', error_type=type(error).__name__, error=str(error))
        save(out / 'ORCHESTRATION_RECEIPT.json', receipt)
        raise
    finally:
        for log in logs:
            if not log.closed:
                log.close()
        lock.close()


if __name__ == '__main__':
    main()
