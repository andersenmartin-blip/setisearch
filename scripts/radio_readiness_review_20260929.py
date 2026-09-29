#!/usr/bin/env python3
"""Read-only budget review of immutable published evidence; no experiment imports.

Prints a reproducible JSON comparison. This is neither an execution gate nor a
new qualification: engineering workloads cannot certify scientific performance.
"""
import hashlib
import json
from pathlib import Path
import subprocess

BASE = '107bbff9462c199795f14b83839ae88ba54f770d'
PATHS = (
    'results_radio_whole_cadence_compact_2026-09-28/phase_budget_proposed.json',
    'results_radio_native_chain_engineering_2026-09-29/disposition.json',
    'results_radio_native_chain_engineering_2026-09-29/closed_error.json',
    'results_radio_event_case_2026-09-29/integration01/result.json',
    'RADIO_WHOLE_CADENCE_INTEGRATION_2026-09-28_DRAFT.md',
    'RADIO_TWO_WEEK_PLAN_2026-09-26.md',
)


def review():
    root = Path(__file__).resolve().parents[1]
    names = [BASE + ':' + path for path in PATHS]
    raw = subprocess.check_output(['git', 'cat-file', '--batch'], cwd=root,
                                  input=('\n'.join(names) + '\n').encode())
    offset = 0
    files = {}
    pins = []
    for path in PATHS:
        end = raw.index(b'\n', offset)
        header = raw[offset:end].split()
        if len(header) != 3 or header[1] != b'blob':
            raise ValueError('Missing immutable input: ' + path)
        size = int(header[2])
        data = raw[end + 1:end + 1 + size]
        offset = end + 2 + size
        if len(data) != size or raw[offset - 1:offset] != b'\n':
            raise ValueError('Truncated Git response')
        git_hash = hashlib.sha1(b'blob ' + str(size).encode() + b'\0' + data).hexdigest()
        if git_hash != header[0].decode():
            raise ValueError('Git identity mismatch')
        files[path] = data
        pins.append({'path': path, 'git_blob': git_hash, 'bytes': size,
                     'sha256': hashlib.sha256(data).hexdigest()})
    if offset != len(raw):
        raise ValueError('Trailing Git response')
    budget, native, error, storage = [json.loads(files[p]) for p in PATHS[:4]]
    phases = budget['phases']
    cal, ev = phases['calibration'], phases['evaluation']
    overhead = budget['overhead']
    total_ms = sum(p['count'] * p['milliseconds_per_case'] for p in phases.values()) + overhead['milliseconds']
    total_bytes = sum(p['count'] * p['bytes_per_case'] for p in phases.values()) + overhead['ledger_bytes'] + overhead['failure_and_summary_bytes']
    if (cal['count'], ev['count'], total_ms, total_bytes) != (127, 24, 7200000, 1024**3):
        raise ValueError('Unexpected frozen scientific budget')
    if native['physical_recovery_gate_measured'] or native['rfi_or_fresh_null_gates_measured']:
        raise ValueError('Unexpected historical qualification')
    if storage['remote_adapter_qualified'] or storage['scientific_127_24_activated']:
        raise ValueError('Unexpected activation')
    refs = error['completed_cases']
    if len(refs) != 4 or any(c['status'] != 'completed' for c in refs):
        raise ValueError('Unexpected engineering reference inventory')
    return {
        'schema': 'radio-readiness-review-v1',
        'source_commit': BASE,
        'status': 'BLOCKED_NO_SCIENTIFIC_OR_TELESCOPE_ADMISSION',
        'input_pins': pins,
        'frozen_budget': {'phases': phases, 'overhead': overhead,
                          'total_milliseconds': total_ms, 'total_evidence_bytes': total_bytes},
        'historical_native': {
            'engineering_reference_count': len(refs),
            'smallest_possible_four_reference_rank': '1/5',
            'required_scientific_rank_ceiling': '1/100',
            'broad_case_partial_milliseconds': native['case4_failed_elapsed_milliseconds'],
            'own_engineering_limit_milliseconds': native['case4_limit_milliseconds'],
            'ratio_to_scientific_evaluation_time_cap': native['case4_failed_elapsed_milliseconds'] / ev['milliseconds_per_case'],
            'retained_on_members_not_final_survivors': native['retained_on'],
            'physical_recovery_or_rfi_null_qualified': False,
        },
        'historical_local_storage': {
            'storage_and_closure_seconds': storage['storage_and_parent_closure_seconds'],
            'case_artifact_bytes': storage['archive_check']['artifact_bytes'],
            'journal_bytes': storage['journal_history_bytes'],
            'own_case_cap_bytes': storage['archive_check']['case_cap_bytes'],
            'arithmetic_headroom_against_scientific_case_bytes': ev['bytes_per_case'] - storage['archive_check']['artifact_bytes'],
            'complete_native_physical_workload': False,
            'remote_adapter_qualified': False,
        },
        'interpretation': [
            'Different historical workloads: do not add their timings or extrapolate 151-case performance.',
            'The native run met its own 240-second case cap; comparison with 80 seconds is not a retroactive failure.',
            'The 24-MiB local storage pass does not qualify the scientific 18-MiB evaluation limit.',
            'Positive arithmetic byte headroom is not a bound on missing receiver/alias/cluster and remote evidence.',
            'The fixed reservations exhaust the total ceiling; no automatic borrowing, refunds or cap changes.',
            'Even a future synthetic pass requires a separate source/acquisition/trial protocol before telescope access.',
        ],
        'outstanding_evidence': [
            'Complete native recovery, receiver/alias/cluster, RFI/null and failure evidence on fresh prospectively fixed engineering identities.',
            'Integrated current-code/runtime, durable remote publication/readback and all scientific case/phase resource limits.',
            'Separately frozen and allocated actual 127-reference/24-evaluation scientific run with a passing fixed gate.',
            'Separately frozen integrated telescope source/acquisition/trial protocol.',
        ],
        'new_random_values': 0, 'new_native_scores': 0, 'new_physical_decisions': 0,
        'new_telescope_reads': 0, 'new_allocations': 0,
        'closed_attempts_reopened': False, 'scientific_limits_changed': False,
        'scientific_127_24_activated': False,
    }


if __name__ == '__main__':
    print(json.dumps(review(), sort_keys=True, indent=2))
