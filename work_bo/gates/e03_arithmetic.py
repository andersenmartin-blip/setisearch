"""Finite deterministic arithmetic engineering; no RNG or telescope inputs.

Execute only after the exact BO source/configuration has been published.
Imports do not create fixtures, load arrays or execute a gate. Legacy guard
violations remain literal FAIL diagnostics; they are never historical repairs.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import sys

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / 'src'))
import methods
import numpy as np

SHAPE = (16, 1048576)
WIDTHS = (1, 3, 9, 33)
STRIDES = (1, 1, 2, 8)
RATE_INDICES = (0, 209, 419, 629, 838)
CONTROL_Q = (63, 64, 65, 127, 129)
EXPECTED_FIXTURE_IDS = ('triangle_v1', 'step_outliers_v1')
OLD_GUARD = 5e-5
NEW_ABSOLUTE_FLOOR = 1e-8
NEW_EPS_MULTIPLIER = 64


def require(value, message):
    if not value:
        raise ValueError(message)


def utc():
    return datetime.now(timezone.utc).isoformat()


def requests_for_normalized_fixture(rates):
    """Declare every selected point before reading any fixture value."""
    requests = []
    times = (np.arange(16, dtype=np.float64) - 7.5) * methods.DT
    for width, stride in zip(WIDTHS, STRIDES, strict=True):
        for rate_index in RATE_INDICES:
            offsets = np.rint(rates[rate_index] * times / methods.DF).astype(np.int32)
            for q in CONTROL_Q:
                grid = np.arange(q * 4096, (q + 1) * 4096, stride, dtype=np.int32)
                indices = np.array([0, len(grid) // 2, len(grid) - 1], dtype=np.int32)
                requests.append(dict(width=width, stride=stride, rate_index=rate_index,
                                     rate=float(rates[rate_index]), offsets=offsets,
                                     q=q, start=q * 4096, stop=(q + 1) * 4096,
                                     selected_indices=indices, centers=grid[indices]))
    return requests


def independent_prefix_at_requests(y, requests):
    """Explicit sequential binary64 prefixes, independent of NumPy cumsum.

    The original legacy boxcar subtracts global prefixes before rounding its
    width result to float32. Replacing that operation by a direct local sum
    would not faithfully reproduce the legacy arithmetic. Only required
    prefix endpoints are retained; each input row is traversed once.
    """
    needed = [set() for _ in range(16)]
    for request in requests:
        width = request['width']
        if width == 1:
            continue
        half = width // 2
        for t, offset in enumerate(request['offsets']):
            for center in request['centers']:
                lo = int(center) + int(offset) - half
                hi = int(center) + int(offset) + half + 1
                require(0 <= lo < hi <= y.shape[1], 'Oracle prefix outside fixture')
                needed[t].update((lo, hi))
    result = []
    for t, positions in enumerate(needed):
        row = y[t]
        running = 0.0
        previous = 0
        values = {0: 0.0}
        for stop in sorted(positions):
            for value in row[previous:stop]:
                running = running + float(value)
            values[stop] = running
            previous = stop
        result.append(values)
    return result


def independent_float32_legacy(y, prefixes, offsets, centers, width):
    """Replay each legacy width/row float32 rounding in explicit order."""
    half = width // 2
    answer = np.empty(len(centers), dtype=np.float32)
    for k, center in enumerate(centers):
        total = np.float32(0)
        for t, offset in enumerate(offsets):
            c = int(center) + int(offset)
            if width == 1:
                width_value = np.float32(y[t, c])
            else:
                difference = prefixes[t][c + half + 1] - prefixes[t][c - half]
                width_value = np.float32(difference)
            total = np.float32(total + width_value)
        answer[k] = total
    return answer


def scalar_reference(y, offsets, center, width):
    half = width // 2
    terms = [float(y[t, int(center) + int(offset) + j])
             for t, offset in enumerate(offsets)
             for j in range(-half, half + 1)]
    expected = math.fsum(terms)
    magnitude = math.fsum(abs(value) for value in terms)
    bound = max(NEW_ABSOLUTE_FLOOR,
                NEW_EPS_MULTIPLIER * np.finfo(np.float64).eps * magnitude)
    return expected, magnitude, float(bound)


def explicit_unguarded_float64(y, offsets, center, width):
    """A diagnostic sequential sum, deliberately without kernel fallback."""
    half = width // 2
    total = 0.0
    for t, offset in enumerate(offsets):
        width_total = 0.0
        for j in range(-half, half + 1):
            width_total = width_total + float(y[t, int(center) + int(offset) + j])
        total = total + width_total
    return total


def verify_normalized_array(path, expected_hash):
    path = Path(path).resolve()
    require(methods.file_sha(path) == expected_hash, 'Normalized fixture bytes differ')
    value = np.load(path, mmap_mode='r', allow_pickle=False)
    require(value.shape == SHAPE and value.dtype == np.dtype('<f4')
            and not value.flags.writeable and value.flags.c_contiguous,
            'Expected immutable full-native software fixture')
    require(np.isfinite(value).all(), 'Nonfinite normalized software fixture')
    return value


def evaluate_fixture(y, requests, kernel, fixture_id, normalization, state,
                     require_fallback=False):
    prefixes = independent_prefix_at_requests(y, requests)
    for width, stride in zip(WIDTHS, STRIDES, strict=True):
        # Prepare each full-native boxcar ONCE, outside all rate/q loops.
        current_prepared = kernel.boxcars(y, width)
        legacy_prepared = methods.legacy_centered_boxcar(y, width)
        state['prepared_fullnative_boxcars'] += 1
        for request in requests:
            if request['width'] != width:
                continue
            offsets, centers = request['offsets'], request['centers']
            grid, grid_fallbacks, grid_bound = kernel.tracks_grid(
                y, current_prepared, offsets, request['start'], request['stop'],
                stride, width)
            selected, selected_fallbacks, selected_bound = kernel.tracks_selected(
                y, current_prepared, offsets, centers, width)
            require(np.array_equal(grid[request['selected_indices']], selected),
                    'Current grid/selected arithmetic differs')
            legacy_grid = methods.legacy_track_sum(
                legacy_prepared, offsets, request['start'], request['stop'], stride)
            legacy_selected = legacy_grid[request['selected_indices']]
            legacy_oracle = independent_float32_legacy(
                y, prefixes, offsets, centers, width)
            require(np.array_equal(legacy_selected, legacy_oracle),
                    'Legacy does not reproduce explicit float32 stage oracle')
            if require_fallback:
                require(current_prepared[1] is not None,
                        'Cancellation fixture failed to request magnitude matrix')
                require(selected_fallbacks == len(centers)
                        and grid_fallbacks == len(grid),
                        'Cancellation fixture did not exercise every expected fallback')
            for k, center in enumerate(centers):
                reference, magnitude, bound = scalar_reference(y, offsets, center, width)
                error = abs(float(selected[k]) - reference)
                legacy_error = abs(float(legacy_selected[k]) - reference)
                require(error <= bound, 'Current math.fsum oracle bound failed')
                old_pass = legacy_error <= OLD_GUARD
                row = dict(fixture=fixture_id, normalization=normalization,
                           width_channels=width, stride=stride,
                           rate_index=request['rate_index'], drift_hz_s=request['rate'],
                           q=request.get('q'), native_center=int(center),
                           current_sum=float(selected[k]), current_fsum_reference=reference,
                           sum_abs_terms=magnitude, current_absolute_error=error,
                           current_frozen_bound=bound, current_bound_pass=True,
                           legacy_sum=float(legacy_selected[k]),
                           legacy_float32_oracle=float(legacy_oracle[k]),
                           legacy_float32_oracle_exact=True,
                           legacy_arithmetic_reproduction_status='PASS',
                           legacy_error_against_fsum=legacy_error,
                           legacy_original_5e_minus5_guard='PASS' if old_pass else 'FAIL',
                           current_selected_fallback_count=selected_fallbacks,
                           current_grid_fallback_count=grid_fallbacks,
                           current_selected_reported_bound=float(selected_bound),
                           current_grid_reported_bound=float(grid_bound))
                if require_fallback:
                    naive = explicit_unguarded_float64(y, offsets, center, width)
                    require(reference == float(8 * width)
                            and float(selected[k]) == reference,
                            'Cancellation fallback result is not exact frozen expectation')
                    require(naive != reference,
                            'Cancellation fixture failed to expose unguarded binary64 loss')
                    require(not old_pass, 'Expected legacy old-guard FAIL was not retained')
                    row.update(expected_fsum=float(8 * width),
                               unguarded_float64_sum=naive,
                               unguarded_float64_loss_observed=True,
                               expected_legacy_guard_failure_observed=True)
                row['legacy_guard_failure_expected_from_frozen_cancellation_case'] = require_fallback
                state['checks'].append(row)
        del current_prepared, legacy_prepared


def make_cancellation_fixture(out):
    """Normalized arithmetic fixture only: it is not a raw-power model."""
    center = 64 * 4096 + 2048
    start, stop = center - 1024, center + 1025
    y = np.zeros(SHAPE, dtype='<f4')
    row_values = (np.float32(2 ** 60), np.float32(1),
                  np.float32(-(2 ** 60)), np.float32(1))
    for t in range(16):
        y[t, start:stop] = row_values[t % 4]
    path = out / 'cancellation_normalized_f32.npy'
    with path.open('xb') as stream:
        np.save(stream, y, allow_pickle=False)
        stream.flush()
        os.fsync(stream.fileno())
    y.flags.writeable = False
    return y, dict(id='cancellation_f32_2pow60_v1', path=str(path.resolve()),
                   sha256=methods.file_sha(path), bytes=path.stat().st_size,
                   shape=list(SHAPE), dtype='<f4', software_normalized_arithmetic_only=True,
                   nonzero_channel_interval_half_open=[start, stop],
                   row_rule='[2**60,1,-2**60,1] repeated four times',
                   expected_fsum_per_width='8*width',
                   expected='Current guard and fallback execute; current equals math.fsum exactly; unguarded binary64 loses terms; legacy old5e-5 guard remains FAIL.')


def cancellation_requests(rates):
    center = 64 * 4096 + 2048
    times = (np.arange(16, dtype=np.float64) - 7.5) * methods.DT
    requests = []
    for width, stride in zip(WIDTHS, STRIDES, strict=True):
        grid = np.arange(center - 64, center + 65, stride, dtype=np.int32)
        indices = np.array([0, len(grid) // 2, len(grid) - 1], dtype=np.int32)
        for rate_index in RATE_INDICES:
            requests.append(dict(width=width, stride=stride, rate_index=rate_index,
                                 rate=float(rates[rate_index]),
                                 offsets=np.rint(rates[rate_index] * times / methods.DF).astype(np.int32),
                                 start=center - 64, stop=center + 65,
                                 selected_indices=indices, centers=grid[indices]))
    return requests


def execute(config_path, out, state):
    config = methods.verify_config(config_path)
    require(any(p['path'] == 'gates/e03_arithmetic.py' for p in config['source_pins']),
            'E03 source must be pinned')
    require(Path(config['gate_outputs']['E03']).resolve() == out,
            'E03 output is not the frozen reserved output')
    require(sys.flags.optimize == 0, 'Unoptimized Python is required')
    state['source_checks'] = methods.verify_sources()
    e02_path, e02 = methods.resolve_e02(config)
    require(tuple(f['id'] for f in e02['fixtures']) == EXPECTED_FIXTURE_IDS,
            'Unexpected deterministic fixture family or order')
    state['E02_result_path'] = str(e02_path / 'RESULT.json')
    state['E02_result_sha256'] = methods.file_sha(e02_path / 'RESULT.json')
    kernel, _normalizer = methods.load_current()
    rates = methods.legacy_drift_grid(16, methods.DT, methods.DF, 4)
    require(len(rates) == 839 and float(rates[0]) == -4 and float(rates[-1]) == 4
            and float(rates[419]) == 0, 'Unexpected fixed drift bank')
    requests = requests_for_normalized_fixture(rates)
    for fixture in e02['fixtures']:
        for normalization in ('legacy', 'current'):
            path = fixture[normalization + '_normalized_path']
            digest = fixture[normalization + '_normalized_sha256']
            y = verify_normalized_array(path, digest)
            evaluate_fixture(y, requests, kernel, fixture['id'], normalization, state)
            require(methods.file_sha(path) == digest,
                    'Normalized fixture changed during arithmetic comparisons')
            del y
    require(len(state['checks']) == 1200, 'Ordinary full-native selected-point count differs')
    ordinary_count = len(state['checks'])
    y, cancel = make_cancellation_fixture(out)
    state['cancellation_fixture'] = cancel
    evaluate_fixture(y, cancellation_requests(rates), kernel,
                     cancel['id'], 'normalized_arithmetic_only', state,
                     require_fallback=True)
    del y
    require(len(state['checks']) - ordinary_count == 60,
            'Cancellation selected-point count differs')
    require(sum(c['legacy_original_5e_minus5_guard'] == 'FAIL'
                for c in state['checks'][ordinary_count:]) == 60,
            'Expected exact count of cancellation legacy guard FAILs differs')
    require(state['prepared_fullnative_boxcars'] == 20,
            'Expected one preparation for each of five matrices and four widths')
    methods.verify_config(config_path)
    methods.resolve_e02(config)
    require(methods.file_sha(out / 'cancellation_normalized_f32.npy') == cancel['sha256'],
            'Cancellation fixture changed')
    return dict(
        schema='SETI_BO_E03_DETERMINISTIC_ARITHMETIC_RESULT_V1', gate='E03', status='PASS',
        completed_utc=utc(), plan_path=str(config_path), plan_sha256=methods.file_sha(config_path),
        source_checks=state['source_checks'], E02_result_path=state['E02_result_path'],
        E02_result_sha256=state['E02_result_sha256'],
        ordinary_selected_points=ordinary_count, cancellation_selected_points=60,
        current_fsum_comparisons=len(state['checks']),
        legacy_explicit_float32_oracle_comparisons=len(state['checks']),
        fullnative_boxcar_preparation_pairs=state['prepared_fullnative_boxcars'],
        current_fullnative_boxcar_preparations=state['prepared_fullnative_boxcars'],
        legacy_fullnative_boxcar_preparations=state['prepared_fullnative_boxcars'],
        total_fullnative_boxcar_preparation_calls=2 * state['prepared_fullnative_boxcars'],
        maximum_current_absolute_error=max(c['current_absolute_error'] for c in state['checks']),
        maximum_legacy_error_against_fsum=max(c['legacy_error_against_fsum'] for c in state['checks']),
        legacy_original_5e_minus5_guard_FAIL_count=sum(
            c['legacy_original_5e_minus5_guard'] == 'FAIL' for c in state['checks']),
        ordinary_legacy_original_guard_FAIL_count=sum(
            c['legacy_original_5e_minus5_guard'] == 'FAIL'
            for c in state['checks'][:ordinary_count]),
        ordinary_legacy_guard_FAILURE_count_not_predetermined=True,
        cancellation_legacy_original_guard_expected_FAIL_count=60,
        cancellation_legacy_original_guard_actual_FAIL_count=sum(
            c['legacy_original_5e_minus5_guard'] == 'FAIL'
            for c in state['checks'][ordinary_count:]),
        cancellation_expected_guard_fallback_and_loss_checks=60,
        current_all_frozen_bounds_pass=True, legacy_all_explicit_stage_oracles_exact=True,
        historical_M_24_raw_sum_failures_preserved=True,
        historical_M_full_QA_design_pass=False,
        original_legacy_absolute_guard=OLD_GUARD,
        new_bound=dict(absolute_floor=NEW_ABSOLUTE_FLOOR,
                       epsilon_multiplier=NEW_EPS_MULTIPLIER,
                       expression='max(1e-8,64*float64_eps*sum_abs_terms)'),
        cancellation_fixture=cancel, selected_checks=state['checks'],
        random_draws=0, astronomical_powers_opened=0, astronomical_sensitivity_or_FAP_qualified=False,
        interpretation='Finite deterministic arithmetic consistency only. Every legacy old-guard failure remains literal FAIL; faithful arithmetic reproduction can pass this distinct engineering gate without passing the original guard. No original M failure or tolerance is changed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    config_path, out = args.config.resolve(), args.out.resolve()
    require(out.is_relative_to(WORK), 'Gate output escapes BO root')
    out.mkdir(parents=True, exist_ok=False)
    state = {'checks': [], 'prepared_fullnative_boxcars': 0}
    code = 0
    try:
        result = execute(config_path, out, state)
    except BaseException as exc:
        code = 1
        result = dict(schema='SETI_BO_E03_DETERMINISTIC_ARITHMETIC_RESULT_V1',
                      gate='E03', status='FAIL', completed_utc=utc(),
                      reason=type(exc).__name__ + ': ' + str(exc),
                      retained_partial_checks=state['checks'],
                      prepared_fullnative_boxcars=state['prepared_fullnative_boxcars'],
                      random_draws=0, astronomical_powers_opened=0,
                      historical_M_failures_unchanged=True)
    result_path = out / 'RESULT.json'
    methods.write_json_exclusive(result_path, result)
    print(json.dumps(dict(event='GATE_TERMINAL_EOF', status=result['status'],
                          result_sha256=methods.file_sha(result_path))), flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
