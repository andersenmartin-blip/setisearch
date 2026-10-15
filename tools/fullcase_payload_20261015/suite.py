"""Five engineering groups, including one complete-footprint guarded fixture."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np

from array_adapter import input_hash, load_typed_array, verify_arrays, write_arrays
from capacity import preadmit
from layout import specs, storage_bounds, values
from runtime import guard, store


def main():
    root = Path(__file__).resolve().parent
    result = root / 'results/suite'; result.mkdir()
    observations = []
    all_specs = specs(); bounds = storage_bounds(all_specs)
    assert len(all_specs) == 498 and bounds['raw_bytes_by_kind']['OFF_inventory'] == 576000000
    assert bounds['all_array_raw_bytes'] == 612781396
    assert len({tuple(s['path']) for s in all_specs}) == 498
    observations.append({'group': 'complete_layout', 'status': 'PASS', 'bounds': bounds})

    small = result / 'small_adapter'; small.mkdir()
    samples = all_specs[-2:] + [
        {'key': 'EMPTY', 'path': ['empty_inventory'], 'shape': [0, 4], 'dtype': '<i8',
         'nbytes': 0, 'kind': 'OFF_inventory', 'pattern_serial': 0},
        {'key': 'SCALAR', 'path': ['scalar'], 'shape': [], 'dtype': '<i8',
         'nbytes': 8, 'kind': 'map', 'pattern_serial': 1}]
    budget = store.Budget(65536)
    descriptors = write_arrays(small / 'valid.npz', samples, values, budget, physical_cap=65536)
    exact = verify_arrays(small / 'valid.npz', descriptors, samples)
    for desc, spec in zip(descriptors, samples):
        recovered = load_typed_array(small / 'valid.npz', desc)
        original = values(spec)
        assert recovered.dtype.str == spec['dtype'] and list(recovered.shape) == spec['shape']
        assert recovered.tobytes() == original.tobytes()
    guard.durable_json(small / 'DESCRIPTORS.json', {'arrays': descriptors, 'verification': exact})
    observations.append({'group': 'empty_scalar_endian_and_edge_bits', 'status': 'PASS', **exact})

    faults = []
    first = samples[0]
    for name, wrong in [('wrong_dtype', np.arange(6, dtype='<u8')),
                        ('wrong_shape', values(first).reshape((2, 3)))]:
        path = small / (name + '.npz')
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            with z.open(first['key'] + '.npy', 'w') as stream:
                np.lib.format.write_array(stream, wrong, version=(1, 0), allow_pickle=False)
        bad = copy.deepcopy(descriptors[:1])
        with zipfile.ZipFile(path) as z:
            bad[0]['NPY_uncompressed_bytes'] = z.getinfo(first['key'] + '.npy').file_size
        try: verify_arrays(path, bad, [first])
        except ValueError as error: faults.append({'fault': name, 'rejected': str(error)})
        else: raise AssertionError(name + ' accepted')
    bad = copy.deepcopy(descriptors);bad[0]['C_order_input_sha256'] = '0' * 64
    try: verify_arrays(small / 'valid.npz', bad, samples)
    except ValueError as error: faults.append({'fault': 'wrong_raw_hash', 'rejected': str(error)})
    else: raise AssertionError('Wrong raw hash accepted')
    try: verify_arrays(small / 'valid.npz', descriptors, samples[:-1])
    except ValueError as error: faults.append({'fault': 'wrong_census', 'rejected': str(error)})
    else: raise AssertionError('Wrong census accepted')
    q = store.Budget(100)
    try: write_arrays(small / 'quota_partial.npz', samples, values, q, physical_cap=100)
    except (ValueError, store.QuotaExceeded) as error:
        assert (small / 'quota_partial.npz').stat().st_size <= 100
        faults.append({'fault': 'quota_exhaustion', 'rejected': str(error), 'partial_retained': True})
    else: raise AssertionError('Quota exhaustion accepted')
    guard.durable_json(small / 'FAULTS.json', {'observations': faults})
    observations.append({'group': 'array_corruption_and_quota_gates', 'status': 'PASS', 'faults': faults})

    capacity = preadmit(bounds['per_case_conditional_bundle_cap_bytes'], 428, 3 * 1024**3,
                         mode='ENGINEERING_COMPARISON_ONLY')
    assert capacity['status'] == 'NOT_ADMITTED_CAPACITY' and capacity['max_slots_at_cap'] == 4
    assert not capacity['any_ledger_read_or_mutated'] and not capacity['production_launched']
    guard.durable_json(result / 'CAPACITY_COMPARISON.json', capacity)
    observations.append({'group': 'all_slots_capacity_gate', 'status': 'PASS', 'capacity': capacity})

    folder = result / 'complete_case'; folder.mkdir()
    source_names = ('layout.py', 'array_adapter.py', 'runtime.py', 'fullcase_worker.py',
                    'capacity.py', 'ARRAY_LAYOUT.json', 'ENGINEERING_SCOPE.json',
                    'SOURCE_DEPENDENCY.json', 'SOURCE_PINS.json')
    request = {'mode': 'COMPLETE_CASE_ENGINEERING_ONLY', 'folder': str(folder),
               'source_pins': {n: store.digest_file(root / n) for n in source_names},
               'reserved_both_child_CPU_s': 480}
    guard.durable_json(folder / 'REQUEST.json', request)
    limit = guard.policy(240, 1800, 1024**3)
    state = {'status': 'RUNNING_PRODUCER', 'producer': None, 'verifier': None,
             'science_admission': False, 'accepted': False,
             'reserved_both_child_CPU_s': 480,
             'per_case_conditional_cap_bytes': bounds['per_case_conditional_bundle_cap_bytes']}
    guard.durable_json(folder / 'STATE.json', state)
    command = [sys.executable, str(root / 'fullcase_worker.py'), 'produce', str(folder / 'REQUEST.json')]
    state['producer'] = copy.deepcopy(guard.run_once(command, folder / 'producer', limit))
    state['status'] = 'PRODUCER_FAILED_RETAINED'
    guard.durable_json(folder / 'STATE.json', state)
    if state['producer']['resource_acceptance']:
        state['status'] = 'RUNNING_VERIFIER'; guard.durable_json(folder / 'STATE.json', state)
        command[2] = 'verify'
        state['verifier'] = copy.deepcopy(guard.run_once(command, folder / 'verifier', limit))
        state['status'] = 'VERIFIER_FAILED_RETAINED'
        guard.durable_json(folder / 'STATE.json', state)
        if state['verifier']['resource_acceptance']:
            check = json.loads((folder / 'VERIFICATION.json').read_text())
            actual = {p.name: {'bytes': p.stat().st_size, 'sha256': store.digest_file(p)}
                      for p in sorted((folder / 'payload').iterdir()) if p.is_file() and not p.is_symlink()}
            assert all(p.is_file() and not p.is_symlink() for p in (folder / 'payload').iterdir())
            assert actual == check['file_inventory']
            assert check['numeric']['arrays_verified'] == 498
            assert check['numeric']['all_raw_array_bytes_verified'] == 612781396
            seal = {'status': 'FULL_CASE_ENGINEERING_TRANSPORT_ONLY', 'science_admission': False,
                    'source_array_layout_sha256': store.digest_file(root / 'ARRAY_LAYOUT.json'),
                    'producer_wait4_sha256': store.digest_file(folder / 'producer/WAIT4_RECEIPT.json'),
                    'verifier_wait4_sha256': store.digest_file(folder / 'verifier/WAIT4_RECEIPT.json'),
                    'verification_sha256': store.digest_file(folder / 'VERIFICATION.json'),
                    'file_inventory': actual}
            guard.durable_json(folder / 'ACCEPTED_ENGINEERING.json', seal)
            state.update(status='FULL_CASE_ENGINEERING_TRANSPORT_ONLY', accepted=True)
    guard.durable_json(folder / 'STATE.json', state)
    observations.append({'group': 'complete_case_guarded_transport',
                         'status': 'PASS' if state['accepted'] else 'FAIL', 'state': state})
    summary = {'status': 'PASS_ENGINEERING_ONLY' if state['accepted'] else 'FAIL_ENGINEERING',
               'groups': observations, 'groups_checked': len(observations),
               'new_scientific_cases_draws_or_seeds': 0, 'new_telescope_bytes': 0,
               'old_bank_resumed': False, 'science_admission': False}
    guard.durable_json(result / 'SUMMARY.json', summary)
    if not state['accepted']: raise SystemExit(1)


if __name__ == '__main__': main()
