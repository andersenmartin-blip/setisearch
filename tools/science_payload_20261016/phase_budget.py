"""Fresh, prospective ENGINEERING reservations; never a science admission.

All four phases are reserved before the first claim. Reservations remain charged
after success, error, partial output, or closure; this API has no retry/reopen or
closed-bank import operation. Files are exclusively created, fsynced, and linked
by hashes. This is an accidental-mutation detector, not protection from an actor
with permission to replace the whole directory.

The caller supplies bounded payload and log writers and the independent process
guard. This module never launches a process and never establishes scientific QA.
"""
from __future__ import annotations

import hashlib
from functools import wraps
import json
import math
import os
from pathlib import Path
import re
import shutil
import threading
import time


MODE = 'ENGINEERING_FIXTURES_ONLY'
FORMAT = 'SETI_FRESH_PHASE_BUDGET_ENGINEERING_V1'
PHASES = ('primary', 'qa', 'exposed', 'exposed_qa')
EVENT_CAP_BYTES = 8192
LEDGER_EVENTS_PER_SLOT = 2
MIN_SLOT_OVERHEAD_BYTES = EVENT_CAP_BYTES * LEDGER_EVENTS_PER_SLOT
MIN_METADATA_RESERVE_BYTES = EVENT_CAP_BYTES * 2
SAFE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$')


class NotAdmitted(ValueError):
    """No new claim or process launch is permitted."""


def _mode(mode):
    if mode != MODE:
        raise NotAdmitted('ENGINEERING_FIXTURES_ONLY required; SCIENCE is not implemented')


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(name + ' must be an integer >= ' + str(minimum))
    return value


def _number(value, name, minimum=0):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value >= minimum
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(name + ' must be finite and >= ' + str(minimum))
    return value


def _encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       allow_nan=False, ensure_ascii=True) + '\n').encode('ascii')


def _sha(value):
    return hashlib.sha256(_encode(value)).hexdigest()


def _receipt_digest(receipt):
    try:
        return _sha(receipt), 'CANONICAL_JSON'
    except (TypeError, ValueError, OverflowError):
        # Invalid guard measurements must still produce a durable failed event.
        return hashlib.sha256(repr(receipt).encode()).hexdigest(), 'REPR_OF_INVALID_RECEIPT'


def _locked(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        if os.getpid() != self._owner_pid:
            raise NotAdmitted('Only the creating parent process owns this fresh ledger')
        with self._lock:
            return method(self, *args, **kwargs)
    return call


def plan_budget(*, primary_count, primary_bound_bytes, primary_cpu_s,
                qa_count, qa_bound_bytes, qa_cpu_s,
                exposed_count, exposed_bound_bytes, exposed_cpu_s,
                exposed_qa_count, exposed_qa_bound_bytes, exposed_qa_cpu_s,
                metadata_reserve_bytes, metadata_cpu_s, log_receipt_overhead_bytes,
                output_limit_bytes, disk_headroom_bytes, cpu_limit_s, mode=MODE):
    """Pure arithmetic; every phase count includes all intended attempts.

    ``*_bound_bytes`` is a payload-only enforced conditional cap, not an expected
    compression ratio. ``log_receipt_overhead_bytes`` includes external logs and
    receipts plus two fixed EVENT_CAP_BYTES ledger allowances per attempt. Both
    metadata and unused per-slot reserves remain charged; no measured CPU credit
    is returned to the plan. Missing/unknown future retries are not admitted.
    """
    _mode(mode)
    _integer(metadata_reserve_bytes, 'metadata_reserve_bytes', MIN_METADATA_RESERVE_BYTES)
    _integer(log_receipt_overhead_bytes, 'log_receipt_overhead_bytes', MIN_SLOT_OVERHEAD_BYTES)
    _integer(output_limit_bytes, 'output_limit_bytes')
    _integer(disk_headroom_bytes, 'disk_headroom_bytes')
    _number(metadata_cpu_s, 'metadata_cpu_s')
    _number(cpu_limit_s, 'cpu_limit_s')
    values = ((primary_count, primary_bound_bytes, primary_cpu_s),
              (qa_count, qa_bound_bytes, qa_cpu_s),
              (exposed_count, exposed_bound_bytes, exposed_cpu_s),
              (exposed_qa_count, exposed_qa_bound_bytes, exposed_qa_cpu_s))
    phases = {}
    for phase, (count, bound, cpu) in zip(PHASES, values):
        _integer(count, phase + '_count')
        _integer(bound, phase + '_bound_bytes', 1)
        _number(cpu, phase + '_cpu_s', 2)
        phases[phase] = {'count': count, 'payload_bound_bytes': bound,
                         'cpu_s_per_slot': cpu,
                         'log_receipt_overhead_bytes_per_slot': log_receipt_overhead_bytes,
                         'external_log_receipt_cap_bytes': log_receipt_overhead_bytes - MIN_SLOT_OVERHEAD_BYTES,
                         'reserved_output_bytes': count * (bound + log_receipt_overhead_bytes),
                         'reserved_cpu_s': count * cpu}
    output = metadata_reserve_bytes + sum(x['reserved_output_bytes'] for x in phases.values())
    try:
        cpu = metadata_cpu_s + math.fsum(x['reserved_cpu_s'] for x in phases.values())
    except OverflowError:
        raise ValueError('Aggregate CPU reservation must be finite') from None
    if not math.isfinite(cpu):
        raise ValueError('Aggregate CPU reservation must be finite')
    errors = []
    if output > output_limit_bytes: errors.append('OUTPUT_LIMIT')
    if output > disk_headroom_bytes: errors.append('DISK_HEADROOM')
    if cpu > cpu_limit_s: errors.append('CPU_LIMIT')
    return {'format': FORMAT, 'mode': mode, 'admitted': not errors,
            'status': 'ENGINEERING_RESERVED_ARITHMETIC_ONLY' if not errors else 'NOT_ADMITTED',
            'errors': errors, 'phases': phases,
            'metadata_reserve_bytes': metadata_reserve_bytes, 'metadata_cpu_s': metadata_cpu_s,
            'total_reserved_output_bytes': output, 'total_reserved_cpu_s': cpu,
            'output_limit_bytes': output_limit_bytes, 'disk_headroom_bytes': disk_headroom_bytes,
            'cpu_limit_s': cpu_limit_s, 'event_cap_bytes': EVENT_CAP_BYTES,
            'reservations_refunded': False, 'scientific_admission': False,
            'closed_banks_read_or_reused': False, 'production_launched': False}


def _canonical_plan(plan):
    """Recompute instead of trusting a caller-edited admitted flag or total."""
    if type(plan) is not dict or plan.get('format') != FORMAT:
        raise ValueError('A canonical fresh engineering phase plan is required')
    args = {}
    for phase in PHASES:
        spec = plan['phases'][phase]
        args[phase + '_count'] = spec['count']
        args[phase + '_bound_bytes'] = spec['payload_bound_bytes']
        args[phase + '_cpu_s'] = spec['cpu_s_per_slot']
    for key in ('metadata_reserve_bytes', 'metadata_cpu_s', 'output_limit_bytes',
                'disk_headroom_bytes', 'cpu_limit_s', 'mode'):
        args[key] = plan[key]
    args['log_receipt_overhead_bytes'] = plan['phases']['primary']['log_receipt_overhead_bytes_per_slot']
    result = plan_budget(**args)
    if result != plan:
        raise ValueError('Plan fields differ from canonical prospective arithmetic')
    return result


def _directory_sync(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def _resource_errors(receipt, reserved_cpu):
    """Recheck authoritative guard fields; never accept only a PASS string."""
    errors = []
    if type(receipt) is not dict:
        return ['MISSING_WHOLE_CHILD_RECEIPT']
    for key, expected in (('wait4_reaped', True), ('watchdog_fired', False),
                          ('launcher_verified', True), ('resource_acceptance', True)):
        if receipt.get(key) is not expected: errors.append('FAILED_' + key)
    if type(receipt.get('exit_code')) is not int or receipt['exit_code'] != 0:
        errors.append('FAILED_exit_code')
    if receipt.get('interruption') is not None:
        errors.append('PARENT_INTERRUPTION')
    if receipt.get('status') != 'RESOURCE_COMPLIANT_ONLY' or receipt.get('errors') != []:
        errors.append('FAILED_GUARD_ASSESSMENT')
    limits = receipt.get('limits')
    if type(limits) is not dict:
        return errors + ['MISSING_GUARD_LIMITS']
    try:
        _number(limits.get('cpu_s'), 'receipt cpu cap', 2)
        _number(limits.get('wall_s'), 'receipt wall cap', 0.000001)
        _integer(limits.get('address_space_bytes'), 'receipt address space cap', 1)
        if limits['cpu_s'] > reserved_cpu: errors.append('CPU_CAP_EXCEEDS_SLOT_RESERVATION')
        for field, cap in (('whole_child_CPU_s', min(reserved_cpu, limits['cpu_s'])),
                           ('wall_s', limits['wall_s']),
                           ('peak_RSS_bytes', limits['address_space_bytes'])):
            _number(receipt.get(field), field)
            if receipt[field] > cap: errors.append('EXCEEDED_' + field)
    except ValueError:
        errors.append('INVALID_WHOLE_CHILD_MEASUREMENT_OR_LIMIT')
    return errors


class PhaseLedger:
    """One fresh serial engineering run, with immutable per-attempt events.

    Keep the owner object for the whole run; construction is via create only.
    A pending claim blocks every other claim. An incomplete or failed run cannot
    be resumed through this API. Durability is before returning the claim to a
    launcher. ``snapshot`` is read-only and verifies the full hash chain.
    """
    def __init__(self, *args, **kwargs):
        raise TypeError('Use PhaseLedger.create for a fresh engineering run')

    @classmethod
    def create(cls, folder, plan, *, mode=MODE):
        _mode(mode)
        plan = _canonical_plan(plan)
        if not plan['admitted']:
            raise NotAdmitted('Whole phase plan does not fit: ' + ','.join(plan['errors']))
        folder = Path(folder)
        if folder.exists() or folder.is_symlink():
            raise NotAdmitted('Fresh ledger directory required; existing/closed banks are never reopened')
        if not folder.parent.is_dir():
            raise ValueError('Ledger parent directory must already exist')
        if shutil.disk_usage(folder.parent).free < plan['total_reserved_output_bytes']:
            raise NotAdmitted('Live disk headroom below the whole prospective reservation')
        folder.mkdir()  # Exclusive fresh ownership; fail before any launch.
        _directory_sync(folder.parent)
        self = object.__new__(cls)
        self.folder = folder.resolve()
        self._owner_pid = os.getpid()
        self._lock = threading.RLock()
        self._expected_events = 0
        self._expected_tip = None
        self._plan_sha = _sha(plan)
        self._append('RESERVATION', {'plan': plan, 'plan_sha256': self._plan_sha})
        return self

    def _read(self):
        files = sorted(self.folder.iterdir())
        if len(files) != self._expected_events:
            raise NotAdmitted('Ledger was truncated, deleted, or appended outside its owner')
        events = []
        previous = None
        for index, path in enumerate(files):
            if path.is_symlink() or not path.is_file() or path.name != f'{index:06d}.json':
                raise NotAdmitted('Unexpected, missing, or nonregular ledger event')
            raw = path.read_bytes()
            if len(raw) > EVENT_CAP_BYTES:
                raise NotAdmitted('Ledger event exceeds its reserved allowance')
            try:
                event = json.loads(raw)
            except ValueError:
                raise NotAdmitted('Invalid immutable ledger JSON') from None
            if type(event) is not dict:
                raise NotAdmitted('Invalid immutable ledger event')
            digest = event.pop('event_sha256', None)
            if (event.get('sequence') != index or event.get('previous_sha256') != previous or
                    digest != _sha(event)):
                raise NotAdmitted('Ledger hash chain differs')
            event['event_sha256'] = digest
            if raw != _encode(event):
                raise NotAdmitted('Immutable ledger event bytes changed')
            events.append(event)
            previous = digest
        if previous != self._expected_tip:
            raise NotAdmitted('Ledger tail differs from the durable owner checkpoint')
        if events:
            initial = events[0]
            if (initial['kind'] != 'RESERVATION' or initial['data']['plan_sha256'] != self._plan_sha or
                    _sha(initial['data']['plan']) != self._plan_sha):
                raise NotAdmitted('Fresh reservation changed')
        return events

    def _append(self, kind, data):
        events = self._read()
        event = {'sequence': len(events), 'kind': kind, 'data': data,
                 'previous_sha256': events[-1]['event_sha256'] if events else None,
                 'written_unix_ns': time.time_ns()}
        event['event_sha256'] = _sha(event)
        raw = _encode(event)
        if len(raw) > EVENT_CAP_BYTES:
            raise ValueError('Event would exceed reserved ledger bytes')
        path = self.folder / f'{len(events):06d}.json'
        with path.open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        _directory_sync(self.folder)
        self._expected_events += 1
        self._expected_tip = event['event_sha256']
        return event

    @_locked
    def snapshot(self):
        events = self._read()
        plan = events[0]['data']['plan']
        claims = {x['data']['claim_id']: x['data'] for x in events if x['kind'] == 'CLAIM'}
        terminals = {x['data']['claim_id']: x['data'] for x in events
                     if x['kind'] in ('COMPLETE', 'PARTIAL_ERROR')}
        stopped = any(x.get('accepted') is not True for x in terminals.values())
        return {'status': ('CLOSED' if events[-1]['kind'] == 'CLOSE' else
                           'STOPPED_RETAINED_NO_RETRY' if stopped else 'OPEN'),
                'plan': plan, 'claims': claims, 'terminals': terminals,
                'pending': sorted(set(claims) - set(terminals)),
                'reserved_output_bytes_retained': plan['total_reserved_output_bytes'],
                'reserved_cpu_s_retained': plan['total_reserved_cpu_s'],
                'recorded_payload_and_external_bytes': sum(
                    x['payload_bytes'] + x['log_receipt_bytes'] for x in terminals.values()),
                'ledger_bytes': sum(x.stat().st_size for x in self.folder.iterdir()),
                'scientific_admission': False, 'events': len(events)}

    @_locked
    def claim(self, phase, case_id):
        state = self.snapshot()
        if state['status'] != 'OPEN' or state['pending']:
            raise NotAdmitted('Run stopped, closed, or awaiting a whole-child terminal receipt')
        if phase not in PHASES:
            raise ValueError('Unknown reserved phase')
        if type(case_id) is not str or SAFE_ID.fullmatch(case_id) is None:
            raise ValueError('Bounded safe case identifier required')
        spec = state['plan']['phases'][phase]
        used = [x for x in state['claims'].values() if x['phase'] == phase]
        if any(x['case_id'] == case_id for x in used):
            raise NotAdmitted('An attempt identifier is spent forever; retries are not admitted')
        if len(used) >= spec['count']:
            raise NotAdmitted('All prospective slots for this phase are spent')
        remaining = (state['reserved_output_bytes_retained'] - state['ledger_bytes'] -
                     state['recorded_payload_and_external_bytes'])
        if shutil.disk_usage(self.folder).free < max(0, remaining):
            raise NotAdmitted('Live disk headroom no longer covers the retained reservation')
        data = {'claim_id': f'{phase}-{len(used):06d}', 'phase': phase, 'case_id': case_id,
                'slot': len(used), 'payload_bound_bytes': spec['payload_bound_bytes'],
                'cpu_s_reserved_no_refund': spec['cpu_s_per_slot'],
                'log_receipt_overhead_bytes_reserved': spec['log_receipt_overhead_bytes_per_slot']}
        self._append('CLAIM', data)
        return data

    @_locked
    def _finish(self, claim_id, receipt, payload_bytes, log_receipt_bytes, error=None):
        _integer(payload_bytes, 'payload_bytes')
        _integer(log_receipt_bytes, 'log_receipt_bytes')
        state = self.snapshot()
        if state['status'] != 'OPEN' or state['pending'] != [claim_id]:
            raise NotAdmitted('Exactly one matching live engineering claim required')
        claim = state['claims'][claim_id]
        spec = state['plan']['phases'][claim['phase']]
        errors = _resource_errors(receipt, spec['cpu_s_per_slot'])
        if payload_bytes > spec['payload_bound_bytes']: errors.append('PAYLOAD_OVERQUOTA')
        if log_receipt_bytes > spec['external_log_receipt_cap_bytes']:
            errors.append('LOG_RECEIPT_OVERQUOTA')
        if error is not None: errors.append('PARTIAL_ERROR_RETAINED')
        receipt_sha, receipt_encoding = _receipt_digest(receipt)
        measured_cpu = receipt.get('whole_child_CPU_s') if type(receipt) is dict else None
        try:
            _number(measured_cpu, 'whole_child_CPU_s')
        except ValueError:
            measured_cpu = None
        data = {'claim_id': claim_id, 'accepted': not errors, 'errors': errors,
                'payload_bytes': payload_bytes, 'log_receipt_bytes': log_receipt_bytes,
                'receipt_sha256': receipt_sha if receipt is not None else None,
                'receipt_digest_encoding': receipt_encoding,
                'whole_child_CPU_s': measured_cpu,
                'error': str(error)[:512] if error is not None else None,
                'error_sha256': hashlib.sha256(str(error).encode()).hexdigest() if error is not None else None,
                'reservations_refunded': False, 'scientific_admission': False}
        return self._append('PARTIAL_ERROR' if error is not None else 'COMPLETE', data)

    def complete(self, claim_id, *, receipt, payload_bytes, log_receipt_bytes=0):
        return self._finish(claim_id, receipt, payload_bytes, log_receipt_bytes)

    def partial_error(self, claim_id, *, error, payload_bytes=0, log_receipt_bytes=0, receipt=None):
        if error is None:
            raise ValueError('A partial failure needs an explicit error')
        return self._finish(claim_id, receipt, payload_bytes, log_receipt_bytes, error)

    @_locked
    def close(self):
        state = self.snapshot()
        if state['status'] == 'CLOSED' or state['pending']:
            raise NotAdmitted('Closed or live claims cannot be closed again')
        counts = {phase: sum(x['phase'] == phase for x in state['claims'].values()) for phase in PHASES}
        complete = (state['status'] == 'OPEN' and all(
            counts[phase] == state['plan']['phases'][phase]['count'] for phase in PHASES))
        return self._append('CLOSE', {'all_reserved_slots_completed_engineering_only': complete,
                'counts': counts, 'prior_status': state['status'],
                'reserved_output_bytes_retained': state['reserved_output_bytes_retained'],
                'reserved_cpu_s_retained': state['reserved_cpu_s_retained'],
                'scientific_admission': False, 'closed_banks_reusable': False})
