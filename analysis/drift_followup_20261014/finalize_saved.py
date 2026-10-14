"""Finalize already-produced drift families after a scalar-boolean JSON failure.

No raw-power or normalization array is loaded, and no source analysis is rerun.
Every saved family is byte-authenticated from the complete PROFILES.json before
its residual arrays are read. Root recovery GO and exact code/metadata hashes
are required. The failed partial file and original source code are preserved.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time

sys.dont_write_bytecode = True
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

ORIGINAL_SHA = '7e1eedc775c48e1b89257f518e04e12f152a4599846c40e177e1aa1196caeee9'
SCOPE_SHA = 'b0a76f82ba0cb901112f94ae6989e64f20b7aa6e395f37d51840ea3d37484075'
CPU_CAP, WALL_CAP, MEMORY_CAP = 60, 120, 2 * 1024**3


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_bytes(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def pin(path, root=None):
    return {'path': path.relative_to(root).as_posix() if root else str(path),
            'bytes': path.stat().st_size, 'sha256': sha(path)}


def conf(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts and
            path.resolve().is_relative_to(root) and not path.is_symlink(), 'Unsafe declared saved-family path')
    return path


def auth(root, declared):
    path = conf(root, declared['path'])
    require(path.is_file() and path.stat().st_size == declared['bytes'] and sha(path) == declared['sha256'],
            'Saved/input artifact byte pin differs: ' + declared['path'])
    return path


def create_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, help='drift_followup directory with saved results')
    parser.add_argument('--inputs-root', required=True, help='Metadata-only original extracted input package')
    parser.add_argument('--portable-inputs', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    for name in ('scope-sha256', 'original-code-sha256', 'corrected-code-sha256', 'finalizer-sha256',
                 'profiles-sha256', 'root-go-sha256'):
        parser.add_argument('--' + name)
    args = parser.parse_args()
    started = time.monotonic()
    root, inputs = Path(args.root).resolve(), Path(args.inputs_root).resolve()
    out = root / 'results'
    scope_path, old_code, corrected_code = root / 'SCOPE.json', root / 'producer_original_execution.py', root / 'producer.py'
    scope = read(scope_path)
    require(sha(scope_path) == SCOPE_SHA and sha(old_code) == ORIGINAL_SHA, 'Original frozen scope/code differs')
    require(args.portable_inputs or scope['source_root'] == str(inputs), 'Original input root differs')
    before = old_code.read_bytes()
    old_bool = b"'signal_only_fine_best_matches_true_activity_window': signal_wi == true_wi,"
    corrected_bool = b"'signal_only_fine_best_matches_true_activity_window': bool(signal_wi == true_wi),"
    require(before.count(old_bool) == 1 and corrected_code.read_bytes() == before.replace(old_bool, corrected_bool),
            'Corrected producer must differ only by scalar bool serialization cast')
    profiles_path = out / 'PROFILES.json'
    profiles = read(profiles_path)
    require(profiles['status'] == 'COMPLETE_54_AUTHENTICATED_PROFILES' and
            profiles['code_sha256'] == ORIGINAL_SHA and profiles['scope_sha256'] == SCOPE_SHA and
            [p['profile_id'] for p in profiles['profiles']] == scope['profile_ids'], 'Completed family metadata differs')
    declared_matrix = next(p for p in scope['input_pins'] if p['path'] == scope['matrix_path'])
    matrix_path = auth(inputs, declared_matrix)
    matrix = read(matrix_path)
    require([p['profile_id'] for p in matrix['profiles']] == scope['profile_ids'], 'Original profile order differs')
    family_pins = [p['family_arrays'] for p in profiles['profiles']]
    require(len(family_pins) == 54 and len({p['path'] for p in family_pins}) == 54, 'Saved family census differs')
    for declared in family_pins:
        auth(out, declared)
    hashes = {'scope_sha256': sha(scope_path), 'original_producer_sha256': sha(old_code),
              'corrected_producer_sha256': sha(corrected_code), 'finalizer_sha256': sha(Path(__file__).resolve()),
              'profiles_sha256': sha(profiles_path)}
    partial = out / 'INJECTIONS.json'
    require(partial.is_file() and not (out / 'failed_INJECTIONS.partial').exists() and
            not (out / 'INJECTIONS.csv').exists() and not (out / 'EXECUTION_RECEIPT.json').exists(),
            'Recovery requires exactly the recorded unfinished injection outputs')
    if args.check_only:
        print(json.dumps({'status': 'PASS_TEXT_ONLY_SAVED_FAMILY_FINALIZER_PREFLIGHT',
                          'raw_power_arrays_opened': False, 'saved_family_arrays_opened': False,
                          'numerical_modules_imported': False, 'authenticated_saved_families': 54,
                          'scope_hashes': hashes, 'original_failed_partial': pin(partial, out),
                          'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': MEMORY_CAP}))
        return
    require(args.scope_sha256 == hashes['scope_sha256'] and args.original_code_sha256 == hashes['original_producer_sha256']
            and args.corrected_code_sha256 == hashes['corrected_producer_sha256'] and args.finalizer_sha256 == hashes['finalizer_sha256']
            and args.profiles_sha256 == hashes['profiles_sha256'], 'Explicit exact recovery code/metadata hash gates required')
    go_path = root / 'FINALIZE_GO.json'
    require(args.root_go_sha256 is not None and sha(go_path) == args.root_go_sha256, 'Exact recovery root GO pin required')
    go = read(go_path)
    require(go['status'] == 'GO_FINALIZE_SAVED_DRIFT_INJECTIONS' and all(go[key] == value for key, value in hashes.items()),
            'Root recovery GO fields differ')
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Recovery wall budget exceeded')))
    signal.alarm(max(1, WALL_CAP - math.ceil(time.monotonic() - started)))
    import numpy as np
    spec = importlib.util.spec_from_file_location('corrected_drift_injection_formatter', corrected_code)
    formatter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(formatter)
    formatter.np = np
    trials = []
    for profile, declared in zip(matrix['profiles'], family_pins):
        with np.load(conf(out, declared['path']), allow_pickle=False) as archive:
            arrays = {key: archive[key] for key in archive.files}
        trials.extend(formatter.injection_trials(profile, arrays))
    require(len(trials) == 3024, 'Recovered trial census differs')
    # Prove all3024 records are strict JSON-serializable before changing outputs.
    recovered = {'schema': 'SETI_RESIDUAL_DOMAIN_DELTA_BIN_INJECTION_TRANSPORT_V1', 'count': 3024,
                 'trials': trials, 'raw_sensitivity_or_FAP_established': False,
                 'instrumental_line_response_modeled': False}
    serialized = json.dumps(recovered, indent=2, sort_keys=True, allow_nan=False) + '\n'
    partial_pin = pin(partial, out)
    partial.rename(out / 'failed_INJECTIONS.partial')
    with partial.open('x', encoding='utf-8') as stream:
        stream.write(serialized)
        stream.flush()
        os.fsync(stream.fileno())
    formatter.write_csv(out / 'INJECTIONS.csv', trials)
    # Authenticate all original science outputs again: recovery must be a
    # serialization-only continuation from already saved spectral analysis.
    for declared in family_pins:
        auth(out, declared)
    require(sha(profiles_path) == hashes['profiles_sha256'], 'Completed family JSON changed during finalization')
    usage = resource.getrusage(resource.RUSAGE_SELF)
    receipt = {'status': 'COMPLETE_BOUNDED_LOCAL_DRIFT_PHASE_PRODUCTION',
               'scope': pin(scope_path), 'producer': pin(old_code), 'source_matrix': declared_matrix,
               'corrected_producer': pin(corrected_code), 'finalizer': pin(Path(__file__).resolve()),
               'root_recovery_go': pin(go_path), 'portable_inputs': args.portable_inputs,
               'actual_input_root': str(inputs), 'original_scope_input_root': scope['source_root'],
               'profiles': 54, 'hypotheses_per_offset_profile': 405,
               'four_row_scores_saved': 54 * 9 * 405 * 7, 'residual_row_terms_saved': 54 * 9 * 405 * 16,
               'injection_trials': 3024, 'raw_data_modified': False, 'input_package_modified': False,
               'detector_producer_imported': False, 'normalization_reused': True,
               'resource_limits': {'CPU_s': 600, 'wall_s': 900, 'memory_bytes': MEMORY_CAP},
               'resource_usage': None,
               'initial_attempt': {'status': 'SAVED_54_FAMILIES_AND_PROFILES_JSON_CSV_THEN_JSON_BOOL_SERIALIZATION_FAILED',
                                   'measured_resource_usage_available': False,
                                   'conservative_budget_charge': {'CPU_s': 600, 'wall_s': 900},
                                   'numerical_producer_sha256': ORIGINAL_SHA,
                                   'failure_stderr': pin(root / 'PRODUCER_STDERR.txt'),
                                   'failure_stdout': pin(root / 'PRODUCER_STDOUT.txt'),
                                   'original_partial_INJECTIONS': partial_pin,
                                   'preserved_partial_INJECTIONS': pin(out / 'failed_INJECTIONS.partial', out)},
               'recovery': {'status': 'FINALIZED_FROM_AUTHENTICATED_SAVED_FAMILIES_ONLY',
                            'scientific_arrays_recomputed': False, 'raw_power_arrays_opened': False,
                            'normalization_arrays_opened': False, 'boolean_cast_only_producer_correction': True,
                            'resource_limits': {'CPU_s': CPU_CAP, 'wall_s': WALL_CAP, 'memory_bytes': MEMORY_CAP},
                            'measured_resource_usage': {'CPU_s': usage.ru_utime + usage.ru_stime,
                                                        'wall_s': time.monotonic() - started, 'peak_RSS_bytes': usage.ru_maxrss * 1024}},
               'outputs': family_pins + [pin(out / name, out) for name in ('PROFILES.json', 'PROFILES.csv', 'INJECTIONS.json', 'INJECTIONS.csv')],
               'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False}
    create_json(out / 'EXECUTION_RECEIPT.json', receipt)
    signal.alarm(0)
    print(json.dumps({'status': receipt['status'], 'recovery': receipt['recovery']}))


if __name__ == '__main__':
    main()
