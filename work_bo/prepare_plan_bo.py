"""Metadata-only BO engineering plan builder; never imports candidate methods."""
from pathlib import Path
import hashlib
import json
import platform
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    destination = ROOT / 'BO_ENGINEERING_PLAN.json'
    if destination.exists():
        raise FileExistsError('Frozen plan candidate already exists; never overwrite it')
    sources = sorted(p for p in ROOT.rglob('*') if p.is_file() and
                     p.suffix in {'.py', '.json', '.md', '.txt'} and
                     not any(s in {'execution', '__pycache__'} for s in p.parts) and
                     p.name not in {'BO_ENGINEERING_PLAN.json', 'PUBLIC_FREEZE_RECEIPT_BO.json'})
    expected_scripts = ['gates/e01_bytes.py', 'gates/e02_normalization.py',
                        'gates/e03_arithmetic.py', 'gates/e04_calibration_time.py',
                        'gates/e05_capture.py', 'run_engineering_bo.py']
    for relative in expected_scripts:
        if not (ROOT / relative).is_file():
            raise FileNotFoundError(relative)
    execution = 'execution/BO_ENGINEERING_V1'
    limits = [(240, 120, 1 << 30, 512 << 20)] + [(300, 180, 2 << 30, 1 << 30)] * 3 + [(120, 60, 512 << 20, 64 << 20)]
    gates = []
    for index, (script, cap) in enumerate(zip(expected_scripts[:5], limits), 1):
        wall, cpu, rss, storage = cap
        gates.append({'id': f'E0{index}', 'script': script,
                      'caps': {'wall_seconds': wall, 'cpu_seconds': cpu,
                               'rss_bytes': rss, 'stored_bytes': storage}})
    plan = {
        'schema': 'SETI_BO_ENGINEERING_PLAN_V1',
        'identity': 'SETI_HIP45688_SAVED_NPY_ENGINEERING_BO_20261030_V1',
        'status': 'FROZEN_CANDIDATE_REQUIRES_PUBLIC_EXACT_READBACK',
        'engineering_only': True,
        'real_telescope_powers_authorized': False,
        'rng_authorized': False,
        'scientific_scores_authorized': False,
        'deterministic_fixture_operations_authorized': ['NPY byte controls', 'full-native normalization', 'explicit sums', 'ESS calibration arithmetic', 'coordinate/support identities', 'fault capture'],
        'execution_relative_dir': execution,
        'gate_outputs': {g['id']: str(ROOT / execution / g['id'] / 'payload') for g in gates},
        'gates': gates,
        'deterministic_group': {'gate_ids': ['E02', 'E03', 'E04'], 'cpu_seconds': 180,
                                'wall_seconds': 300, 'rss_bytes': 2 << 30, 'stored_bytes': 1 << 30},
        'capture': {'max_stdout_bytes': 4 << 20, 'failure_reserve_bytes': 1 << 20, 'poll_seconds': 0.02},
        'resource_accounting': {'CPU_scope': 'capture parent CPU plus child-tree CPU; exact wait4 user/system on closure and validated live process-tree sampling',
                                'process_identity': 'Resolve host procfs identity through own NSpid/PPid/session bindings; host PIDs are read-only sampling identifiers, never signal targets.',
                                'cleanup': 'Only validated owned process groups in the caller PID namespace may receive signals.',
                                'failure_reserve': 'One fixed 1 MiB run footer is reserved before children; gate/group stored-byte limits count their own outputs. No automatic cap increase.'},
        'source_pins': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in sources],
        'runtime': {'python_version': platform.python_version(), 'numpy_version': np.__version__,
                    'python_executable_sha256': sha(Path(sys.executable))},
        'thread_environment': {name: '1' for name in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS']},
        'case_contract': 'The exact pinned gate sources define deterministic fixtures, fixed probes and expected acceptance/rejection cases. No input-dependent case choice or threshold change is allowed.',
        'numerical_bound': {'current': 'abs(error) <= max(1e-8, 64*float64_eps*sum_abs_terms)',
                            'legacy_original_absolute_guard': 5e-5,
                            'legacy_failure_retention': 'Each original failure remains FAIL. A faithful legacy comparator does not requalify old M.'},
        'ordering': 'E01 then E02 then E03 then E04 then E05; exact child exit and output audited before next gate. Any failure stops this identity; no automatic retry, overwrite or cap increase.',
        'input_exclusions': ['All astronomical powers, including HIP45688 raw DATA ZIP/NPYs', 'Protected HIP98505 2016/native156/native159 and 2019 context', 'Original M launchers/run identities', 'B06/restoration failed identities'],
        'preserved_history': {'HIP45688_M_raw_sum_failures': 24, 'HIP45688_M_full_QA': False,
                              'all_M_raw_sum_failures': 142, 'BA_unique_archive_IDs': 486,
                              'BA_technical_MHz_visits': 268.50128173828125},
        'new_observations': 0, 'new_archive_requests': 0, 'new_coverage_credit': 0, 'cost_DKK': 0,
        'next_gates_not_authorized_by_this_plan': ['24 limited paired synthetic six-scan cases', '2 full 839-rate paired cases', 'Actual HIP45688 input activation', 'Astronomical search'],
        'interpretation': 'PASS establishes only the explicit deterministic engineering checks. It is not signal recovery, calibrated FAP, sensitivity, statistical qualification or a new SETI result.'
    }
    with destination.open('x') as stream:
        stream.write(json.dumps(plan, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({'plan': str(destination), 'sha256': sha(destination), 'source_count': len(sources), 'astronomical_values_opened': 0, 'RNG_draws': 0}))

if __name__ == '__main__':
    main()
