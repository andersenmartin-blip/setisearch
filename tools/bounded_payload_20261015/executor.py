"""Engineering-only integration of guarded producer, verifier and acceptance."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from payload_store import digest_file

GUARD_PATH = Path(__file__).resolve().parent.parent / 'whole_child_guard_20261015/guard.py'
GUARD_SHA256 = 'd02505861e9a5b3883708836e39b6a8712d56f983c740897857bb0f6e201e492'
if digest_file(GUARD_PATH) != GUARD_SHA256:
    raise RuntimeError('Previously tested process guard bytes differ')
spec = importlib.util.spec_from_file_location('seti_pinned_whole_child_guard', GUARD_PATH)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def regular_bytes(root):
    return sum(p.stat().st_size for p in Path(root).rglob('*')
               if p.is_file() and not p.is_symlink())


def run_jobs(root, jobs, *, mode, CPU_envelope_s, output_cap_bytes):
    if mode != 'ENGINEERING_FIXTURES_ONLY':
        raise ValueError('No scientific admission or production dispatcher is implemented')
    if type(output_cap_bytes) is not int or output_cap_bytes <= 0:
        raise ValueError('Positive output cap required')
    if not guard.finite_nonnegative(CPU_envelope_s):
        raise ValueError('Finite CPU envelope required')
    for job in jobs:
        if (type(job['records']) is not int or not 0 <= job['records'] <= 61440 or
                type(job['payload_cap_bytes']) is not int or job['payload_cap_bytes'] <= 0 or
                job.get('fault') not in (None, 'tamper', 'CPU_after_payload')):
            raise ValueError('Invalid bounded engineering fixture request')
        guard.policy(job['CPU_s'], job['wall_s'], 1024**3)
    root = Path(root).resolve()
    root.mkdir()
    source = Path(__file__).resolve().parent
    state = {'status': 'RUNNING', 'mode': mode, 'jobs': [], 'unsubmitted': list(range(len(jobs))),
             'running': None, 'whole_child_CPU_s': 0, 'CPU_envelope_s': CPU_envelope_s,
             'output_cap_bytes': output_cap_bytes, 'science_admission': False,
             'code_sha256': {n: digest_file(source / n)
                             for n in ('executor.py', 'payload_store.py', 'fixture_worker.py')},
             'pinned_guard_sha256': GUARD_SHA256}
    guard.durable_json(root / 'STATE.json', state)
    for index, job in enumerate(jobs):
        limits = guard.policy(job['CPU_s'], job['wall_s'], 1024**3)
        # Reserve BOTH producer and verifier before any producer execution.
        if state['whole_child_CPU_s'] + 2 * job['CPU_s'] > CPU_envelope_s:
            state['status'] = 'STOPPED_CPU_RESERVATION'
            break
        # Fixed pinned-fixture source/log/receipt allowance, not free payload.
        if regular_bytes(root) + job['payload_cap_bytes'] + 2 * 1024**2 > output_cap_bytes:
            state['status'] = 'STOPPED_OUTPUT_RESERVATION'
            break
        folder = root / f'job_{index:04d}'
        folder.mkdir()
        payload = folder / 'payload'
        state['unsubmitted'].remove(index)
        state['running'] = {'index': index, 'phase': 'producer',
                            'reserved_producer_and_verifier_CPU_s': 2 * job['CPU_s']}
        guard.durable_json(root / 'STATE.json', state)
        request = {**job, 'payload': str(payload), 'job_root': str(folder),
                   'mode': mode, 'code_sha256': state['code_sha256']}
        guard.durable_json(folder / 'REQUEST.json', request)
        command = [sys.executable, str(source / 'fixture_worker.py'),
                   'produce', str(folder / 'REQUEST.json')]
        producer = guard.run_once(command, folder / 'producer', limits)
        state['whole_child_CPU_s'] += producer['whole_child_CPU_s'] or 0
        record = {'index': index, 'producer': producer, 'verifier': None,
                  'accepted': False, 'status': 'PRODUCER_FAILED'}
        state['jobs'].append(record)
        if producer['resource_acceptance']:
            state['running']['phase'] = 'verifier'
            guard.durable_json(root / 'STATE.json', state)
            command[2] = 'verify'
            verifier = guard.run_once(command, folder / 'verifier', limits)
            state['whole_child_CPU_s'] += verifier['whole_child_CPU_s'] or 0
            record['verifier'] = verifier
            record['status'] = 'VERIFIER_FAILED'
            if verifier['resource_acceptance']:
                receipt = json.loads((folder / 'VERIFICATION.json').read_text())
                if receipt['status'] != 'TRANSPORT_INTEGRITY_ONLY':
                    raise RuntimeError('Verifier did not close with transport integrity')
                # Bind the complete unchanged post-verification byte inventory.
                actual = {p.name: {'bytes': p.stat().st_size, 'sha256': digest_file(p)}
                          for p in payload.iterdir() if p.is_file() and not p.is_symlink()}
                if any(p.is_symlink() or not p.is_file() for p in payload.iterdir()):
                    raise RuntimeError('Non-regular entry after verifier closure')
                if actual != receipt['verified_file_inventory']:
                    raise RuntimeError('Payload changed after verifier closure')
                if regular_bytes(root) > output_cap_bytes:
                    raise RuntimeError('Whole execution output cap exceeded')
                seal = {'status': 'RESOURCE_AND_PAYLOAD_INTEGRITY_ONLY',
                        'science_admission': False, 'scientific_QA': False,
                        'producer_receipt_sha256': digest_file(folder / 'producer/WAIT4_RECEIPT.json'),
                        'verifier_receipt_sha256': digest_file(folder / 'verifier/WAIT4_RECEIPT.json'),
                        'verification_sha256': digest_file(folder / 'VERIFICATION.json'),
                        'manifest_sha256': receipt['manifest_sha256']}
                guard.durable_json(folder / 'ACCEPTED_ENGINEERING.json', seal)
                record.update(accepted=True, status=seal['status'])
        state['running'] = None
        guard.durable_json(root / 'STATE.json', state)
        if not record['accepted']:
            state['status'] = 'STOPPED_RETAINED_NO_RETRY'
            break
    if state['status'] == 'RUNNING':
        state['status'] = 'COMPLETE_ENGINEERING_ONLY'
    guard.durable_json(root / 'STATE.json', state)
    return state
