"""Standalone synthetic regression tests for independent_dual_max.

No telescope, source, detector, producer, saved-map, or injection array is read.
Check-only parses Python source and reports the test contract without importing
NumPy or QA. Arithmetic is gated by the exact root GO and frozen QA/test hashes.
The brute oracle uses scalar Python loops, inclusive integer boxes, and built-in
round; it shares no prefix-sum, winner-traversal, or DC-mask code with QA.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time


FIELDS = {
    'score': 'float64',
    'drift_grid_index': 'int16',
    'window_start_row': 'int16',
    'width_channels': 'int16',
    'valid_hypothesis_count': 'int64',
}
STARTS = (0, 2, 4, 6, 8, 10, 12)
WIDTHS = (1, 3)
GO_STATUS = 'GO_FULL_DUAL_QA_SYNTHETIC_TESTS'
CAPS = {'CPU_cap_s': 60, 'wall_cap_s': 90,
        'memory_cap_bytes': 512 * 1024**2, 'output_cap_bytes': 1024**2}
CASES = (
    'zero_exact_tie_order',
    'positive_tie_earliest_window_and_drift',
    'deterministic_dyadic_matrix_no_dc',
    'inclusive_right_dc_boundary_alternative',
    'inclusive_left_dc_boundary_alternative',
    'reference_row_fixed_dc_always_empty',
    'crop_edge_support_counts',
    'adjustable_frequency_axis_and_times',
    'absolute_half_to_even_before_odd_crop',
    'all_tracks_outside_crop_raw_and_clean_empty',
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def brute_dual_max(z, frequencies, crop0, drift_grid, times, dc_channels,
                   fch1=0.0, df=-1.0, starts=STARTS, widths=WIDTHS):
    """Scalar-loop oracle; no NumPy reductions or vectorized track geometry."""
    columns = len(z[0])
    result = {name: {key: [] for key in FIELDS} for name in ('raw', 'clean')}
    for frequency in frequencies:
        winners = {
            name: {'score': -math.inf, 'drift_grid_index': -1,
                   'window_start_row': -1, 'width_channels': -1,
                   'valid_hypothesis_count': 0}
            for name in ('raw', 'clean')
        }
        base = (float(frequency) - float(fch1)) / float(df)
        for start in starts:
            for width in widths:
                radius = width // 2
                for drift_index, drift in enumerate(drift_grid):
                    # Round the complete absolute mapping before crop removal.
                    centers = [round(base + float(drift) * float(t) / float(df))
                               for t in times]
                    if any(center - radius < crop0 or
                           center + radius >= crop0 + columns
                           for center in centers):
                        continue
                    touched = any(center - radius <= dc <= center + radius
                                  for center in centers for dc in dc_channels)
                    total = 0.0
                    for row, center in enumerate(centers):
                        for absolute_channel in range(center - radius,
                                                      center + radius + 1):
                            total += float(z[start + row][absolute_channel - crop0])
                    score = total / math.sqrt(len(times) * width)
                    for name in ('raw', 'clean'):
                        if name == 'clean' and touched:
                            continue
                        winner = winners[name]
                        winner['valid_hypothesis_count'] += 1
                        if score > winner['score']:
                            winner.update(score=score, drift_grid_index=drift_index,
                                          window_start_row=start,
                                          width_channels=width)
        for name, winner in winners.items():
            for key, value in winner.items():
                result[name][key].append(value)
    return result


def assert_matches(np, actual, expected, case):
    require(isinstance(actual, dict) and set(actual) == {'raw', 'clean'},
            case + ': dual family schema differs')
    for family in ('raw', 'clean'):
        require(isinstance(actual[family], dict) and
                set(actual[family]) == set(FIELDS),
                case + ': field schema differs for ' + family)
        for field, dtype in FIELDS.items():
            value = actual[family][field]
            require(isinstance(value, np.ndarray), case + ': array required for ' + field)
            require(value.dtype == np.dtype(dtype), case + ': dtype differs for ' + field)
            reference = np.asarray(expected[family][field], dtype=dtype)
            require(value.shape == reference.shape, case + ': shape differs for ' + field)
            if field == 'score':
                require(not np.isnan(value).any(), case + ': NaN score')
                require(np.allclose(value, reference, atol=1e-12, rtol=1e-12),
                        case + ': score differs for ' + family)
            else:
                require(np.array_equal(value, reference),
                        case + ': ' + field + ' differs for ' + family)
        counts = actual[family]['valid_hypothesis_count']
        empty = counts == 0
        require(np.isfinite(actual[family]['score'][~empty]).all(),
                case + ': nonfinite nonempty maximum')
        require(np.isneginf(actual[family]['score'][empty]).all(),
                case + ': EMPTY score must be negative infinity')
        for field, sentinel in (('drift_grid_index', -1), ('window_start_row', -1),
                                ('width_channels', -1)):
            require(np.all(actual[family][field][empty] == sentinel),
                    case + ': EMPTY sentinel differs for ' + field)


def run_synthetic_regressions(np, helper):
    drift_grid = np.linspace(-4.0, 4.0, 159, dtype=np.float64)
    times = np.asarray([0.0, 1.0, 2.0, 3.0], dtype=np.float64)
    records = []

    def exercise(case, z, references, crop0, dc_channels=(), fch1=0.0,
                 df=-1.0, sample_times=times):
        z = np.asarray(z, dtype=np.float64)
        references = tuple(int(channel) for channel in references)
        frequencies = np.asarray([fch1 + df * channel for channel in references],
                                 dtype=np.float64)
        require(z.ndim == 2 and z.shape[0] == 16, case + ': synthetic shape differs')
        expected = brute_dual_max(z.tolist(), frequencies.tolist(), crop0,
                                  drift_grid.tolist(), sample_times.tolist(),
                                  tuple(dc_channels), fch1=fch1, df=df)
        actual = helper(z, frequencies, crop0, drift_grid, sample_times,
                        tuple(dc_channels), fch1=fch1, df=df,
                        starts=STARTS, widths=WIDTHS)
        assert_matches(np, actual, expected, case)
        records.append({'case': case, 'carriers': len(references),
                        'raw_valid_hypotheses': int(actual['raw']['valid_hypothesis_count'].sum()),
                        'clean_valid_hypotheses': int(actual['clean']['valid_hypothesis_count'].sum()),
                        'status': 'PASS'})
        return actual

    # Every hypothesis is exactly zero: strict-greater updates must preserve
    # the first window, narrowest width, and first ascending drift index.
    zero = exercise(CASES[0], np.zeros((16, 64)), (1020, 1028), 1000)
    for family in ('raw', 'clean'):
        require(np.all(zero[family]['score'] == 0.0), 'Zero tie score differs')
        require(np.all(zero[family]['window_start_row'] == 0), 'Earliest window tie differs')
        require(np.all(zero[family]['width_channels'] == 1), 'Width1 tie differs')
        require(np.all(zero[family]['drift_grid_index'] == 0), 'Ascending drift tie differs')
        require(np.all(zero[family]['valid_hypothesis_count'] == 2226), 'Full family count differs')

    # Two positive equal maxima in nonoverlapping windows. The first drift
    # whose four rounded centers remain fixed is index76, before exact zero.
    tied = np.zeros((16, 64), dtype=np.float64)
    for row in (0, 1, 2, 3, 12, 13, 14, 15):
        tied[row, 24] = 2.0
    positive = exercise(CASES[1], tied, (1024,), 1000)
    for family in ('raw', 'clean'):
        require(positive[family]['score'][0] == 4.0, 'Positive tie score differs')
        require(positive[family]['window_start_row'][0] == 0, 'Positive earliest window differs')
        require(positive[family]['width_channels'][0] == 1, 'Positive narrow winner differs')
        require(positive[family]['drift_grid_index'][0] == 76, 'Positive ascending drift differs')

    # Dyadic entries give exact scalar/prefix sums, including negatives and
    # nontrivial winners, without decimal accumulation obscuring tie order.
    dyadic = np.asarray([[(row * 13 + column * 7) % 31 / 8.0 - 15.0 / 8.0
                          for column in range(96)] for row in range(16)], dtype=np.float64)
    no_dc = exercise(CASES[2], dyadic, (1020, 1035, 1056, 1070), 1000)
    for field in FIELDS:
        require(np.array_equal(no_dc['raw'][field], no_dc['clean'][field]),
                'DC-unaffected raw/clean equality differs for ' + field)

    # A spike only in source row0 is available solely to window0. Every width1
    # track misses it because its reference center is1040, whereas every width3
    # track contains the adjacent DC at the inclusive reference-row boundary.
    # Clean maximization must recover an admissible zero-score width1 track.
    for case, dc in ((CASES[3], 1041), (CASES[4], 1039)):
        spike = np.zeros((16, 80), dtype=np.float64)
        spike[0, dc - 1000] = 16.0
        boundary = exercise(case, spike, (1040,), 1000, (dc,))
        require(boundary['raw']['window_start_row'][0] == 0, case + ': raw boundary window differs')
        require(boundary['raw']['width_channels'][0] == 3, case + ': width3 boundary winner absent')
        require(boundary['raw']['score'][0] > 0.0, case + ': raw boundary score absent')
        require(boundary['clean']['score'][0] == 0.0, case + ': clean alternative not recovered')
        require(boundary['clean']['window_start_row'][0] == 0 and
                boundary['clean']['width_channels'][0] == 1 and
                boundary['clean']['drift_grid_index'][0] == 0,
                case + ': clean alternative tie order differs')
        require(0 < boundary['clean']['valid_hypothesis_count'][0] < 2226,
                case + ': inclusive DC clean count differs')

    # Every track contains its unchanged reference-row center at times[0]=0.
    # A fixed DC carrier therefore has no clean hypothesis at any drift/window.
    empty = exercise(CASES[5], dyadic, (1020, 1040, 1070), 1000, (1032, 1040, 1052))
    require(empty['raw']['valid_hypothesis_count'][1] == 2226, 'DC raw count differs')
    require(empty['clean']['valid_hypothesis_count'][1] == 0, 'Fixed DC carrier is not EMPTY')
    require(np.isneginf(empty['clean']['score'][1]), 'Fixed DC EMPTY score differs')
    require(empty['clean']['drift_grid_index'][1] == -1 and
            empty['clean']['window_start_row'][1] == -1 and
            empty['clean']['width_channels'][1] == -1, 'Fixed DC EMPTY tuple differs')
    require(empty['clean']['valid_hypothesis_count'][0] > 0 and
            empty['clean']['valid_hypothesis_count'][2] > 0,
            'Nearby non-DC carriers lost all clean hypotheses')

    # Support validity includes the complete inclusive box in every row.
    # The final carrier first fits at drift76, whose displacement rounds zero.
    edge = exercise(CASES[6], np.zeros((16, 17)), (1000, 1001, 1008, 1015, 1016), 1000)
    require(np.all((edge['raw']['valid_hypothesis_count'] > 0) &
                   (edge['raw']['valid_hypothesis_count'] < 2226)),
            'Crop-edge support must remove some hypotheses and retain others')
    require(edge['raw']['drift_grid_index'][-1] == 76, 'Right crop edge earliest valid drift differs')
    for field in FIELDS:
        require(np.array_equal(edge['raw'][field], edge['clean'][field]),
                'Crop-edge no-DC equality differs for ' + field)

    exercise(CASES[7], dyadic, (1020, 1035, 1056), 1000, (1040,),
             fch1=512.0, df=-2.0,
             sample_times=np.asarray([0.0, 0.5, 1.5, 2.5], dtype=np.float64))

    # At the first drift, centers are1020,1020,1022,1022. Subtracting the
    # odd crop1001 before half-to-even rounding would instead select different
    # cells in all three non-reference rows and miss the planted maximum.
    half = np.zeros((16, 64), dtype=np.float64)
    for row, channel, power in ((0, 1020, 1.0), (1, 1020, 2.0),
                                (2, 1022, 4.0), (3, 1022, 8.0)):
        half[row, channel - 1001] = power
    rounded = exercise(CASES[8], half, (1020,), 1001,
                       sample_times=np.asarray([0.0, 0.125, 0.375, 0.625], dtype=np.float64))
    for family in ('raw', 'clean'):
        require(rounded[family]['score'][0] == 7.5, 'Absolute half-to-even score differs')
        require(rounded[family]['drift_grid_index'][0] == 0 and
                rounded[family]['window_start_row'][0] == 0 and
                rounded[family]['width_channels'][0] == 1,
                'Absolute half-to-even planted winner differs')

    outside = exercise(CASES[9], np.zeros((16, 17)), (950, 1060), 1000)
    for family in ('raw', 'clean'):
        require(np.all(outside[family]['valid_hypothesis_count'] == 0),
                'Out-of-crop tracks must all be EMPTY')
        require(np.isneginf(outside[family]['score']).all(), 'Out-of-crop EMPTY score differs')
        for field in ('drift_grid_index', 'window_start_row', 'width_channels'):
            require(np.all(outside[family][field] == -1), 'Out-of-crop EMPTY tuple differs')
    require(tuple(record['case'] for record in records) == CASES, 'Synthetic case census differs')
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--root-go', type=Path)
    parser.add_argument('--root-go-sha256')
    parser.add_argument('--qa-sha256')
    parser.add_argument('--test-sha256')
    args = parser.parse_args()
    own_path = Path(__file__).resolve()
    qa_path = own_path.with_name('qa_v2.py')
    ast.parse(own_path.read_text(encoding='utf-8'), filename=str(own_path))
    if args.check_only:
        print(json.dumps({'status': 'PASS_METADATA_ONLY_SYNTHETIC_QA_TEST_CONTRACT',
                          'qa_path': str(qa_path), 'cases': list(CASES),
                          'shape_rows': 16, 'window_starts': list(STARTS),
                          'widths': list(WIDTHS), 'drifts': 159,
                          'return_fields': FIELDS,
                          'empty_tuple': {'score': '-inf', 'drift_grid_index': -1,
                                          'window_start_row': -1, 'width_channels': -1,
                                          'valid_hypothesis_count': 0},
                          'root_go_status': GO_STATUS,
                          'caps': CAPS,
                          'source_values_read': False,
                          'numerical_tests_executed': False}, sort_keys=True))
        return
    for name in ('root_go_sha256', 'qa_sha256', 'test_sha256'):
        require(isinstance(getattr(args, name), str) and
                re.fullmatch('[0-9a-f]{64}', getattr(args, name)),
                'Exact root GO, QA, and test SHA256s required before arithmetic')
    require(args.root_go is not None and args.root_go.is_file(), 'Exact root GO file required')
    require(digest(args.root_go) == args.root_go_sha256, 'Root GO bytes differ')
    require(digest(qa_path) == args.qa_sha256, 'Frozen QA bytes differ')
    require(digest(own_path) == args.test_sha256, 'Frozen synthetic test bytes differ')
    root_go = json.loads(args.root_go.read_bytes())
    require(isinstance(root_go, dict) and root_go.get('status') == GO_STATUS,
            'Root GO does not authorize these synthetic regression tests')
    require(root_go.get('qa_sha256') == args.qa_sha256 and
            root_go.get('test_sha256') == args.test_sha256, 'Root GO source pins differ')
    require(isinstance(root_go.get('public_commit'), str) and
            re.fullmatch('[0-9a-f]{40}', root_go['public_commit']),
            'Public-freeze commit pin required')
    require(root_go.get('caps') == CAPS, 'Root GO synthetic resource caps differ')
    started = time.monotonic()
    for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[key] = '1'
    resource.setrlimit(resource.RLIMIT_CPU, (CAPS['CPU_cap_s'], CAPS['CPU_cap_s']))
    resource.setrlimit(resource.RLIMIT_AS, (CAPS['memory_cap_bytes'], CAPS['memory_cap_bytes']))
    signal.alarm(CAPS['wall_cap_s'])
    import numpy as np
    spec = importlib.util.spec_from_file_location('seti_burst_full_independent_qa', qa_path)
    qa = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = qa
    spec.loader.exec_module(qa)
    qa.np = np
    records = run_synthetic_regressions(np, qa.independent_dual_max)
    payload = json.dumps({'status': 'PASS_INDEPENDENT_DUAL_MAX_SYNTHETIC_REGRESSIONS',
                          'source_values_read': False,
                          'numerical_tests_executed': True,
                          'root_go_sha256': args.root_go_sha256,
                          'qa_sha256': args.qa_sha256,
                          'test_sha256': args.test_sha256,
                          'public_commit': root_go['public_commit'],
                          'elapsed_wall_s': time.monotonic() - started,
                          'caps': CAPS, 'cases': records}, sort_keys=True)
    require(len(payload.encode()) + 1 <= CAPS['output_cap_bytes'], 'Synthetic output budget exceeded')
    signal.alarm(0)
    print(payload)


if __name__ == '__main__':
    main()
