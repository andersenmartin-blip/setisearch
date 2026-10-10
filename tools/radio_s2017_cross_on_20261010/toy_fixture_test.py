#!/usr/bin/env python3
"""Synthetic pure-math tests; never import matcher or read its live inputs.

Root may run this once after all source peers PASS. The only target file read is
the pinned Python source. Five allowlisted function definitions are AST-extracted
into an isolated toy namespace. No target module/main, contract, generator,
np.load, file pin reader, detector, profile or source loader is called.
"""
import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import time

EXPECTED_SOURCE_SHA = '8ec587be2e0cccd7a443373dbb5b466da9554576beeb019c91b59a3eee746a62'
FUNCTIONS = ('require', 'sorted_bins', 'directed_nearest', 'consistent_triples', 'top_records')
CPU_CAP, WALL_CAP, MEMORY_CAP = 10, 30, 1073741824


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def extract_pure_functions(path, expected_sha, np, start_wall):
    check(path.is_absolute() and path.resolve() == path and path.is_file(), 'Canonical source path required')
    raw = path.read_bytes()
    check(len(raw) < 131072 and hashlib.sha256(raw).hexdigest() == expected_sha == EXPECTED_SOURCE_SHA,
          'Exact reviewed matcher source required')
    tree = ast.parse(raw, filename=str(path))
    definitions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    check(all(name in definitions for name in FUNCTIONS), 'Allowlisted pure definitions missing')
    main_guards = [node for node in tree.body if isinstance(node, ast.If)
                   and ast.dump(node.test, include_attributes=False)
                   == ast.dump(ast.parse("__name__ == '__main__'", mode='eval').body, include_attributes=False)]
    check(len(main_guards) == 1 and len(main_guards[0].body) == 1
          and isinstance(main_guards[0].body[0], ast.Expr)
          and isinstance(main_guards[0].body[0].value, ast.Call)
          and isinstance(main_guards[0].body[0].value.func, ast.Name)
          and main_guards[0].body[0].value.func.id == 'main', 'Expected inert main guard missing')
    forbidden = {'main', 'load_contract', 'load_maxima', 'recheck_inputs', 'verify_pin',
                 'checked_file', 'digest', 'read_json', 'open', 'exec', 'eval', '__import__',
                 'Path', 'save_new', 'save_atomic', 'publish_terminal'}
    nodes = [definitions[name] for name in FUNCTIONS]
    for node in nodes:
        check(not node.decorator_list, 'Pure definition has a decorator')
        for descendant in ast.walk(node):
            check(not isinstance(descendant, (ast.Import, ast.ImportFrom)), 'Pure function imports a module')
            check(not (isinstance(descendant, ast.Name) and descendant.id in forbidden),
                  'Pure function references forbidden I/O or execution')
            check(not (isinstance(descendant, ast.Attribute) and descendant.attr in
                       {'load', 'save', 'fromfile', 'tofile', 'read_bytes', 'write_bytes', 'read_text', 'write_text'}),
                  'Pure function references forbidden data-file access')

    def enforce_usage(_start_cpu, _start_wall):
        check(time.process_time() < CPU_CAP, 'Toy fixture CPU cap exceeded')
        check(time.monotonic() - start_wall < WALL_CAP, 'Toy fixture wall cap exceeded')
        check(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 <= MEMORY_CAP,
              'Toy fixture RSS cap exceeded')

    namespace = {'np': np, 'N': 3, 'GRID_COUNT': 785, 'TOP_COUNT': 1000,
                 'ONS': ('epoch1_on', 'epoch2_on', 'epoch3_on'),
                 'FAMILY': 'radio_s2017_cross_on_20261010', 'C0': 179306496, 'CORE': 4096,
                 'FCH1': 2802832031.25, 'DF': -2.7939677238464355,
                 'enforce_usage': enforce_usage}
    module = ast.Module(body=nodes, type_ignores=[])
    exec(compile(module, '<AST-extracted-pinned-pure-functions-only>', 'exec'), namespace)
    return namespace, {name: hashlib.sha256(ast.dump(definitions[name], include_attributes=False).encode()).hexdigest()
                       for name in FUNCTIONS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matcher-source', type=Path, required=True)
    parser.add_argument('--expected-matcher-sha256', required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    start_wall = time.monotonic()
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    import numpy as np
    check(np.__version__ == '2.3.5', 'Exact reviewed NumPy runtime required for toy fixtures')
    ns, function_hashes = extract_pure_functions(args.matcher_source, args.expected_matcher_sha256, np, start_wall)
    passed = []
    scope = {'ON_reference_seconds_from_anchor': [0.0, 10.0, 20.0]}
    grid = np.linspace(-4.0, 4.0, 785, dtype=np.float64)

    def setup(n=3):
        ns['N'] = n
        return np.arange(ns['C0'] + ns['CORE'], ns['C0'] + ns['CORE'] + n, dtype=np.int64)

    def scan(frequencies, indices=None, scores=None, widths=None):
        n = len(frequencies)
        return {'fstar': np.asarray(frequencies, dtype=np.float64),
                'drift_indices': np.asarray(indices if indices is not None else [2] * n, dtype=np.int16),
                'scores': np.asarray(scores if scores is not None else [1.0] * n, dtype=np.float64),
                'widths': np.asarray(widths if widths is not None else [1] * n, dtype=np.int16)}

    def nearest(source, target, channels, tau):
        return ns['directed_nearest'](source, target, ns['sorted_bins'](source, channels, np),
                                      ns['sorted_bins'](target, channels, np), channels, tau, np, 0.0, start_wall)

    channels = setup()
    # Exact inclusive frequency boundary, including its immediate outer neighbor.
    for value, expected in [(2.5, 0), (-2.5, 0), (float(np.nextafter(2.5, np.inf)), -1)]:
        p = nearest(scan([0, 10000, 20000]), scan([value, 5000, 30000]), channels, 2.5)
        check(int(p[0]) == expected, 'Inclusive frequency boundary failed')
    for delta, expected in [(-1, 0), (0, 0), (1, 0), (2, -1)]:
        p = nearest(scan([0, 10000, 20000]), scan([0, 5000, 30000], [2 + delta, 2, 2]), channels, 2.5)
        check(int(p[0]) == expected, 'Drift-index inclusion boundary failed')
    for k, l in [(0, 1), (784, 783)]:
        p = nearest(scan([0, 10000, 20000], [k, k, k]), scan([0, 5000, 30000], [l, l, l]), channels, 2.5)
        check(int(p[0]) == 0, 'Drift grid endpoint failed')
    passed.append('inclusive_frequency_and_drift_boundaries')

    query = scan([10, 1000, 3000])
    check(int(nearest(query, scan([9, 12, 2000], [1, 2, 2]), channels, 5)[0]) == 0,
          'Frequency gap must dominate drift gap')
    check(int(nearest(query, scan([9, 11, 2000], [1, 2, 2]), channels, 5)[0]) == 1,
          'Drift gap must dominate global channel')
    check(int(nearest(query, scan([11, 9, 2000]), channels, 5)[0]) == 0,
          'Final equal-gap tie must choose minimum global channel')
    passed.append('frequency_primary_tie_order')

    tied = scan([5, 5, 2000])
    for value, tau, expected in [(11, 6, 0), (5, 0, 0), (4, 1, 0), (2100, 100, 2)]:
        p = nearest(scan([value, 10000, 30000]), tied, channels, tau)
        check(int(p[0]) == expected, 'Duplicate predecessor/exact hit or outside array endpoint failed')
    passed.append('duplicate_frequency_predecessor_group')

    first = nearest(query, scan([11, 9, 2000], scores=[-100, 1000, 0], widths=[3, 1, 3]), channels, 5)
    second = nearest(query, scan([11, 9, 2000], scores=[1000, -100, 0], widths=[1, 3, 1]), channels, 5)
    check(np.array_equal(first, second), 'Scores/widths changed partner selection')
    passed.append('score_and_width_do_not_select_neighbor')

    triple_scans = [scan([0, 1000, 3000], [0, 0, 0]), scan([4, 1200, 3200], [0, 0, 0]),
                    scan([-3, 5, 3400], [0, 0, 0])]
    pairs = {(a, b): nearest(triple_scans[a], triple_scans[b], channels, 5)
             for a, b in ((0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1))}
    check(int(pairs[0, 1][0]) == int(pairs[1, 0][0]) == 0, 'A0/B0 mutual fixture missing')
    check(int(pairs[0, 2][0]) == int(pairs[2, 0][0]) == 0, 'A0/C0 mutual fixture missing')
    check(int(pairs[1, 2][0]) == 1 and int(pairs[2, 1][1]) == 0, 'B0/C1 mutual fixture missing')
    check(ns['consistent_triples'](triple_scans, pairs, 5, np).shape == (0, 3),
          'Distinct mutual pair edges must not be synthesized into a triple')
    passed.append('pairwise_mutual_but_no_consistent_triple')

    coherent_scans = [scan([0, 1000, 3000]), scan([0, 1200, 3200]), scan([0, 1400, 3400])]
    coherent = {key: np.array([0, -1, -1], dtype=np.int32) for key in pairs}
    relation = ns['consistent_triples'](coherent_scans, coherent, 5, np)
    check(np.array_equal(relation, np.array([[0, 0, 0]], dtype='<i4')) and relation.dtype.str == '<i4',
          'Valid all-six-links triple was not retained with exact indices/dtype')
    for key in coherent:
        damaged = {name: values.copy() for name, values in coherent.items()}
        damaged[key][0] = 1
        check(ns['consistent_triples'](coherent_scans, damaged, 5, np).shape == (0, 3),
              'A changed directional link did not reject triple')
    ranged = [scan([0, 1000, 3000]), scan([5, 1200, 3200]), scan([10, 1400, 3400])]
    check(ns['consistent_triples'](ranged, coherent, 5, np).shape == (0, 3), 'Full frequency span was not checked')
    drifted = [scan([0, 1000, 3000], [0, 0, 0]), scan([0, 1200, 3200], [1, 1, 1]),
               scan([0, 1400, 3400], [2, 2, 2])]
    check(ns['consistent_triples'](drifted, coherent, 5, np).shape == (0, 3), 'Full drift span was not checked')
    identities = {key: np.arange(3, dtype=np.int32) for key in pairs}
    complete = ns['consistent_triples']([scan([0, 10, 20])] * 3, identities, 0, np)
    check(complete.shape == (3, 3) and all(len(np.unique(complete[:, s])) == 3 for s in range(3)),
          'One-to-one relation failed')
    passed.append('all_six_links_exact_and_one_to_one')

    absent = nearest(scan([0, 10, 20], [0, 0, 0]), scan([0, 10, 20], [4, 4, 4]), channels, 1)
    check(np.all(absent == -1), 'Empty neighboring drift bins must keep partners absent')
    no_links = {key: np.full(3, -1, dtype=np.int32) for key in pairs}
    empty = ns['consistent_triples'](coherent_scans, no_links, 5, np)
    check(empty.shape == (0, 3) and empty.dtype.str == '<i4', 'Empty relation schema failed')
    check(ns['top_records'](empty, coherent_scans, channels, grid, scope, np) == [], 'Empty ranking failed')
    passed.append('empty_bins_and_zero_relation')

    ranked_scans = [scan([0, 10, 20], scores=[100, 6, -1], widths=[1, 3, 1]),
                    scan([0, 10, 20], scores=[5, 6, -2], widths=[3, 1, 3]),
                    scan([0, 10, 20], scores=[5, 6, -3], widths=[1, 3, 1])]
    identity_relation = np.column_stack([np.arange(3, dtype=np.int32)] * 3)
    records = ns['top_records'](identity_relation, ranked_scans, channels, grid, scope, np)
    check([row['descriptive_minimum_saved_score'] for row in records] == [6, 5, -3], 'Minimum score ordering failed')
    check([row['members'][0]['global_carrier_vector_index'] for row in records] == [1, 0, 2], 'Display ranking index failed')
    for row in records:
        for si, member in enumerate(row['members']):
            index = member['global_carrier_vector_index']
            check(member['saved_maximum_robust_box_track_score'] == float(ranked_scans[si]['scores'][index]),
                  'Original member score changed')
            check(member['original_key']['width_channels'] == int(ranked_scans[si]['widths'][index])
                  and member['original_key']['drift_grid_index'] == 2
                  and member['original_key']['reference_seconds_from_anchor'] == scope['ON_reference_seconds_from_anchor'][si],
                  'Original member key changed')
    tied_scans = [scan([0, 10, 20], scores=[3, 3, 3])] * 3
    reverse = identity_relation[::-1].copy()
    tied_records = ns['top_records'](reverse, tied_scans, channels, grid, scope, np)
    check([row['members'][0]['global_carrier_vector_index'] for row in tied_records] == [0, 1, 2],
          'Equal-minimum score channel tie order failed')
    passed.append('minimum_score_display_order')

    channels = setup(1001)
    large_relation = np.column_stack([np.arange(1001, dtype=np.int32)] * 3)[::-1].copy()
    original_bytes = large_relation.tobytes()
    large_scans = [scan(np.arange(1001), scores=[2] * 1001)] * 3
    records = ns['top_records'](large_relation, large_scans, channels, grid, scope, np)
    check(len(records) == 1000 and [row['display_rank'] for row in records] == list(range(1, 1001)),
          'Fixed top1000 display cap/ranks failed')
    check([row['members'][0]['global_carrier_vector_index'] for row in records] == list(range(1000)),
          'Deterministic cutoff tie failed')
    check(large_relation.tobytes() == original_bytes and len(large_relation) == 1001,
          'Display cap mutated full relation')
    passed.append('fixed_top1000_and_full_relation')

    ns['enforce_usage'](0.0, start_wall)
    receipt = {'status': 'PASS_NINE_SYNTHETIC_PURE_MATH_FIXTURE_CASES_NO_LIVE_INPUTS',
               'matcher_source_sha256': EXPECTED_SOURCE_SHA, 'extracted_function_AST_sha256': function_hashes,
               'test_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'passed_test_ids': passed, 'passed_case_count': len(passed),
               'target_module_imported': False, 'target_main_or_gate_or_generator_called': False,
               'live_npz_or_other_scientific_input_read': False, 'detector_or_profile_imported': False,
               'synthetic_numpy_runtime': np.__version__, 'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP,
               'memory_cap_bytes': MEMORY_CAP, 'process_CPU_seconds': time.process_time(),
               'wall_seconds': time.monotonic() - start_wall,
               'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    check(args.receipt.is_absolute() and args.receipt.parent.resolve() == args.receipt.parent,
          'Canonical private receipt location required')
    with args.receipt.open('x', encoding='utf-8') as handle:
        json.dump(receipt, handle, indent=2, allow_nan=False)
        handle.write('\n')
    signal.alarm(0)
    print(json.dumps({'status': receipt['status'], 'passed_case_count': len(passed),
                      'process_CPU_seconds': time.process_time()}))


if __name__ == '__main__':
    main()
