"""Bounded geometry-only diagnosis of 19 missing native-bin rounding cells.

No observed residual or score member is decoded. Previous data stay read-only.
Exact affine strips use dyadic constants from stored floats; legacy float64
rounding coordinates are checked independently rather than silently replaced.
"""
from __future__ import annotations

import argparse
import csv
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import resource
import signal
import time

import numpy as np


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def frac(value):
    return F.from_float(float(value))


def nearest_even(x):
    lower = x.numerator // x.denominator
    remainder = x - lower
    if remainder < F(1, 2):
        return lower
    if remainder > F(1, 2):
        return lower + 1
    return lower if lower % 2 == 0 else lower + 1


def rational(x):
    return {'numerator': str(x.numerator), 'denominator': str(x.denominator), 'value': float(x)}


def clip(poly, aa, bb, cc):
    """Intersect a convex closed polygon with aa*delta+bb*phase+cc >= 0."""
    result = []
    for start, end in zip(poly, poly[1:] + poly[:1]):
        vs = aa * start[0] + bb * start[1] + cc
        ve = aa * end[0] + bb * end[1] + cc
        if vs >= 0:
            result.append(start)
        if (vs < 0 <= ve) or (ve < 0 <= vs):
            lam = vs / (vs - ve)
            result.append((start[0] + lam * (end[0] - start[0]),
                           start[1] + lam * (end[1] - start[1])))
    unique = []
    for point in result:
        if not unique or point != unique[-1]:
            unique.append(point)
    if len(unique) > 1 and unique[0] == unique[-1]:
        unique.pop()
    return unique


def phase_interval(rows, delta):
    lower = [(F(-1, 2), True, 'phase_box_lower')]
    upper = [(F(1, 2), True, 'phase_box_upper')]
    for row in rows:
        even = row['target'] % 2 == 0
        lower.append((-row['b'] - F(1, 2) - row['a'] * delta, even, f"row{row['row']}_lower"))
        upper.append((-row['b'] + F(1, 2) - row['a'] * delta, even, f"row{row['row']}_upper"))
    lo, hi = max(v[0] for v in lower), min(v[0] for v in upper)
    lo_active = [v for v in lower if v[0] == lo]
    hi_active = [v for v in upper if v[0] == hi]
    lo_closed, hi_closed = all(v[1] for v in lo_active), all(v[1] for v in hi_active)
    nonempty = lo < hi or (lo == hi and lo_closed and hi_closed)
    return lo, hi, lo_closed, hi_closed, nonempty, [v[2] for v in lo_active], [v[2] for v in hi_active]


def interval_json(interval):
    lo, hi, lc, hc, nonempty, lower_labels, upper_labels = interval
    return {'lower': rational(lo), 'upper': rational(hi), 'lower_included': lc,
            'upper_included': hc, 'nonempty': nonempty,
            'width': float(max(F(0), hi - lo)),
            'active_lower_constraints': lower_labels, 'active_upper_constraints': upper_labels}


def includes(interval, phase):
    lo, hi, lc, hc, nonempty, *_ = interval
    return nonempty and (lo < phase or (lo == phase and lc)) and (phase < hi or (phase == hi and hc))


def drift_at_phase(rows, phase, half):
    low, high = -half, half
    low_closed = high_closed = True
    for row in rows:
        aa, cc = row['a'], row['b'] + phase
        for a, c in ((aa, cc + F(1, 2)), (-aa, F(1, 2) - cc)):
            closed = row['target'] % 2 == 0
            if a > 0:
                value = -c / a
                if value > low:
                    low, low_closed = value, closed
                elif value == low:
                    low_closed = low_closed and closed
            elif a < 0:
                value = -c / a
                if value < high:
                    high, high_closed = value, closed
                elif value == high:
                    high_closed = high_closed and closed
            else:
                require(c > 0 or (c == 0 and closed), 'Truth phase has no feasible drift')
    return {'lower_delta_hz_s': rational(low), 'upper_delta_hz_s': rational(high),
            'lower_included': low_closed, 'upper_included': high_closed,
            'width_hz_s': float(high - low)}


METHOD = """# Geometry-only rounding-cell diagnosis

The former 405-point family was a Cartesian lattice in drift and reference
phase. A bound below half a native channel on the *unrounded coordinate error*
does not guarantee the same rounded channel: a true coordinate may sit much
closer to a half-integer boundary. Matching a four-row native delta response
requires one lattice point inside the intersection of all four rounding strips.
That intersection can be narrow and slanted, and the lattice can miss it.

For a fixed active four-row window, write the source coordinate in row i as
N + (d0 + delta)*t_i/DF + phase. Here N is the original integer source reference
channel plus the frozen injection host offset512; delta is in Hz/s, phase in
native channels, and t_i is the original midpoint-relative time in seconds.
The parameter box is delta in[-4/158,+4/158], phase in[-0.5,+0.5]. A target native
channel k has the strip k-0.5 <= coordinate <= k+0.5. Both endpoints are included
for even k and excluded for odd k, preserving nearest-integer ties-to-even.

This run intersects the four strips with the box using exact rational polygon
clipping. Stored floating constants are interpreted as exact binary rational
numbers. The previous NumPy float64 expression has intermediate rounding;
its stored405 geometries and truth centers are checked separately. The exact
affine model is therefore stated explicitly and is not substituted for an old
result. Closed polygon vertices are closure geometry; endpoint flags separately
specify the actual half-open strips. Every19 truth point is strictly feasible.

## Proposed finite-complete four-row arrangement

1. Enumerate every half-integer line that crosses the parameter box in any
   of the four rows. Each has phase = k+0.5-N-d0*t_i/DF-delta*t_i/DF.
2. Collect exact critical delta coordinates: both box endpoints; every line
   crossing either phase-box edge; every pairwise line intersection inside
   the closed box. Deduplicate and sort all rational values.
3. At each critical delta and each midpoint between consecutive critical
   deltas, sort the in-box phase boundaries plus both phase-box endpoints.
   Evaluate every boundary phase and every open phase-interval midpoint.
4. Round all four exact rational coordinates ties-to-even, then deduplicate
   the resulting four-integer tuples while retaining a parameter witness.
   Include boundary samples: open-cell samples alone can miss tie-only tuples.

Between consecutive critical delta values, line order and incidences do not
change. Every two-dimensional cell and one-dimensional slanted/horizontal
stratum intersects its midpoint vertical slice; critical slices also capture
vertices and vertical box edges. Sampling all phase strata on these slices
therefore covers every rounded four-row tuple of the declared exact affine
family. This is a finite arrangement method, not a claim that any fixed Cartesian
mesh is complete. A later implementation must check its code, limits, parity
boundary behavior, and relationship to legacy float64 semantics before scoring.

Only existing injection truth, coordinate arrays and metadata were analyzed.
No spectral power, normalized residual or observed score member was decoded;
there is no new sky result, observation, sensitivity or FAP. Original arrays and
the former run remain unchanged. The arrangement is proposed, not executed here.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--params-sha256', required=True)
    parser.add_argument('--code-sha256', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    params_path = root / 'rounding_followup/PARAMS.json'
    require(sha(params_path) == args.params_sha256, 'Geometry scope byte pin mismatch')
    require(sha(Path(__file__)) == args.code_sha256, 'Geometry code byte pin mismatch')
    params = json.loads(params_path.read_text())
    resource.setrlimit(resource.RLIMIT_CPU, (params['CPU_seconds_cap'], params['CPU_seconds_cap']))
    signal.alarm(params['wall_seconds_cap'])
    before_wall, before_cpu = time.monotonic(), time.process_time()
    for pin in params['input_pins']:
        path = root / pin['path']
        require(path.stat().st_size == pin['bytes'] and sha(path) == pin['sha256'], 'Input byte pin mismatch: ' + pin['path'])
    context = json.loads((root / params['input_pins'][1]['path']).read_text())
    profiles = {p['profile_id']: p for p in context['profiles']}
    prior = json.loads((root / params['input_pins'][0]['path']).read_text())
    require(len(profiles) == 54 and len(prior['trials']) == 3024, 'Input census mismatch')
    distinct = {}
    for trial in prior['trials']:
        key = (trial['profile_id'], trial['true_drift_fraction_of_half_original_step'],
               trial['true_phase_channels'], trial['true_window_start_row'])
        if key in distinct:
            previous = distinct[key]
            for field in ('true_absolute_centers', 'true_active_source_rows',
                          'signal_only_fine_best_matching_active4_count'):
                require(previous[field] == trial[field], 'Amplitude duplicate geometry differs')
        else:
            distinct[key] = trial
    require(len(distinct) == 1512, 'Distinct geometry census mismatch')
    failed = [t for t in distinct.values() if t['signal_only_fine_best_matching_active4_count'] < 4]
    require(len(failed) == 19, 'Missing geometry census mismatch')
    half, df = frac(params['geometry']['delta_drift_half_width_hz_s']), frac(params['geometry']['DF_hz'])
    reports, cache, exact_diff_count = [], {}, 0
    for trial in failed:
        profile_id = trial['profile_id']
        p = profiles[profile_id]
        track = p['selected_track']
        if profile_id not in cache:
            path = root / 'drift_followup/results/profiles' / (profile_id + '_family.npz')
            with np.load(path, allow_pickle=False) as archive:
                cache[profile_id] = {field: archive[field] for field in params['read_NPZ_fields']}
        arrays = cache[profile_id]
        times = arrays['times_from_primary_reference_s']
        require(times.tolist() == p['times_from_primary_reference_s'], 'Original time convention differs')
        host_i = int(np.flatnonzero(arrays['offset_channels'] == 512)[0])
        centers = arrays['rounded_absolute_centers'][host_i]
        require(centers.shape == (405, 16), 'Coordinate family dimensions differ')
        active = trial['true_active_source_rows']
        k = np.asarray(trial['true_absolute_centers'], dtype=np.int64)
        legacy = np.rint(track['source_reference_channel'] + 512 + trial['true_phase_channels']
                         + trial['true_drift_hz_s'] * times / float(df)).astype(np.int64)
        require(np.array_equal(legacy, k), 'Legacy truth coordinates differ')
        counts = (centers[:, active] == k[active]).sum(axis=1)
        prior_max = trial['signal_only_fine_best_matching_active4_count']
        require(int(counts.max()) == prior_max and not np.isin(centers[:, active], (178782208, 179830784, 180879360)).any(),
                'Prior geometry maximum or DC eligibility differs')
        n, d0 = F(track['source_reference_channel'] + 512), frac(track['drift_hz_s'])
        truth_delta, truth_phase = frac(trial['true_drift_hz_s']) - d0, frac(trial['true_phase_channels'])
        truth_x = [n + frac(trial['true_drift_hz_s']) * frac(t) / df + truth_phase for t in times]
        require([nearest_even(x) for x in truth_x] == k.tolist(), 'Exact affine truth differs from legacy truth')
        rows = [{'row': row, 'a': frac(times[row]) / df,
                 'b': n + d0 * frac(times[row]) / df - int(k[row]), 'target': int(k[row])} for row in active]
        poly = [(-half, F(-1, 2)), (half, F(-1, 2)), (half, F(1, 2)), (-half, F(1, 2))]
        for row in rows:
            poly = clip(poly, row['a'], F(1), row['b'] + F(1, 2))
            poly = clip(poly, -row['a'], F(-1), F(1, 2) - row['b'])
            require(poly, 'Continuous truth cell unexpectedly empty')
        area = abs(sum(x[0] * y[1] - y[0] * x[1] for x, y in zip(poly, poly[1:] + poly[:1]))) / 2
        require(area > 0 and -half < truth_delta < half and F(-1, 2) < truth_phase < F(1, 2), 'Truth is not strictly within parameter box')
        margins = [F(1, 2) - abs(truth_x[row] - int(k[row])) for row in active]
        require(min(margins) > 0, 'Truth point touches rounding boundary')
        witness_delta = sum(x[0] for x in poly) / len(poly)
        witness_phase = sum(x[1] for x in poly) / len(poly)
        require(all(nearest_even(n + (d0 + witness_delta) * frac(times[row]) / df + witness_phase) == int(k[row]) for row in active),
                'Feasible cell witness does not match all four rows')
        lattice_intersections, exact_grid_matches = [], []
        for di in range(81):
            delta = frac(arrays['family_drift_hz_s'][di * 5]) - d0
            interval = phase_interval(rows, delta)
            if interval[4]:
                captured_phases = [float(ph) for ph in arrays['family_phase_channels'][di * 5:di * 5 + 5] if includes(interval, frac(ph))]
                lattice_intersections.append({'drift_index': di, 'delta_drift_hz_s': float(delta),
                                              'total_drift_hz_s': float(d0 + delta),
                                              'phase_interval': interval_json(interval),
                                              'captured_existing_phase_values': captured_phases})
            for pi in range(5):
                hi = di * 5 + pi
                phase = frac(arrays['family_phase_channels'][hi])
                exact_tuple = [nearest_even(n + (d0 + delta) * frac(times[row]) / df + phase) for row in active]
                differences = sum(int(exact_tuple[i] != centers[hi, row]) for i, row in enumerate(active))
                exact_diff_count += differences
                exact_grid_matches.append(sum(int(exact_tuple[i] == k[row]) for i, row in enumerate(active)))
        require(max(exact_grid_matches) == prior_max, 'Exact affine grid outcome differs from legacy stored grid')
        require(not any(v['captured_existing_phase_values'] for v in lattice_intersections), 'Former lattice enters supposedly missing truth cell')
        di = int(np.argmin(np.abs(arrays['family_drift_hz_s'][::5] - trial['true_drift_hz_s'])))
        pi = int(np.argmin(np.abs(arrays['family_phase_channels'][:5] - trial['true_phase_channels'])))
        hi = di * 5 + pi
        near_drift, near_phase = frac(arrays['family_drift_hz_s'][hi]), frac(arrays['family_phase_channels'][hi])
        errors, crossings = [], []
        for row in active:
            nx = n + near_drift * frac(times[row]) / df + near_phase
            error = nx - truth_x[row]
            errors.append(abs(error))
            if int(centers[hi, row]) != int(k[row]):
                crossings.append({'row': row, 'truth_channel': int(k[row]), 'nearest_lattice_channel': int(centers[hi, row]),
                                  'truth_distance_to_half_integer_channels': float(F(1, 2) - abs(truth_x[row] - int(k[row]))),
                                  'signed_continuum_lattice_error_channels': float(error)})
        report = {'profile_id': profile_id, 'origin_scan_id': trial['origin_scan_id'], 'context_scan_id': trial['context_scan_id'],
                  'origin_rank': trial['origin_rank'], 'active_start_row': trial['true_window_start_row'], 'active_rows': active,
                  'true_drift_fraction_of_half_step': trial['true_drift_fraction_of_half_original_step'],
                  'true_drift_hz_s': trial['true_drift_hz_s'], 'true_delta_drift_hz_s': rational(truth_delta),
                  'true_phase_channels': trial['true_phase_channels'], 'true_active_absolute_centers': k[active].tolist(),
                  'former405_best_matching_rows': prior_max, 'former405_best_matching_fraction': prior_max / 4,
                  'exact_affine405_best_matching_rows': max(exact_grid_matches),
                  'continuous_cell_area_hz_s_times_channel': rational(area),
                  'drift_projection_delta_hz_s': [float(min(x[0] for x in poly)), float(max(x[0] for x in poly))],
                  'phase_projection_channels': [float(min(x[1] for x in poly)), float(max(x[1] for x in poly))],
                  'closure_polygon_vertices': [{'delta_drift_hz_s': rational(x[0]), 'phase_channels': rational(x[1])} for x in poly],
                  'truth_min_rounding_boundary_margin_channels': float(min(margins)),
                  'truth_row_boundary_margins_channels': [float(m) for m in margins],
                  'phase_interval_at_truth_drift_channels': interval_json(phase_interval(rows, truth_delta)),
                  'drift_interval_at_truth_phase': drift_at_phase(rows, truth_phase, half),
                  'strict_interior_witness': {'delta_drift_hz_s': rational(witness_delta), 'total_drift_hz_s': float(d0 + witness_delta),
                                              'phase_channels': rational(witness_phase)},
                  'existing81_drift_slices_intersecting_cell': lattice_intersections,
                  'existing405_points_inside_actual_four_row_cell': 0,
                  'nearest_cartesian_lattice_hypothesis': hi,
                  'nearest_cartesian_lattice_matching_rows': int(counts[hi]),
                  'nearest_cartesian_continuum_max_error_channels': float(max(errors)),
                  'nearest_cartesian_boundary_crossings': crossings,
                  'cell_constraints': [{'row': row['row'], 'target_channel': row['target'],
                                        'a_seconds_per_hertz': rational(row['a']), 'b_channels': rational(row['b']),
                                        'strip_endpoints_included': row['target'] % 2 == 0} for row in rows]}
        reports.append(report)
    out = root / 'rounding_followup/geometry_results'
    out.mkdir(exist_ok=False)
    result = {'schema': 'SETI_EXISTING19_ROUNDING_CELL_GEOMETRY_DIAGNOSIS_V1', 'status': 'PASS_GEOMETRY_ONLY_CONTINUOUS19_FEASIBLE_FORMER405_MISSES',
              'unique_injection_geometries': 1512, 'reported_missing_geometries': 19,
              'amplitude_duplicates_per_geometry': 2, 'diagnosed_profiles': len(cache),
              'missing_matching_count_distribution': {str(k): sum(r['former405_best_matching_rows'] == k for r in reports) for k in (2, 3)},
              'exact_affine_vs_legacy_coordinate_differences_active_rows': exact_diff_count,
              'all19_continuous_truth_points_strictly_feasible': True, 'all19_former405_cell_intersections': 0,
              'minimum_truth_rounding_boundary_margin_channels': min(r['truth_min_rounding_boundary_margin_channels'] for r in reports),
              'maximum_nearest_cartesian_continuum_error_channels': max(r['nearest_cartesian_continuum_max_error_channels'] for r in reports),
              'diagnoses': reports, 'new_observed_scores_computed': 0, 'new_raw_reads': 0,
              'finite_complete_arrangement_executed': False, 'original_arrays_modified': False,
              'params_sha256': args.params_sha256, 'code_sha256': args.code_sha256}
    (out / 'DIAGNOSIS19.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    fields = ['profile_id', 'active_start_row', 'true_drift_fraction_of_half_step', 'true_phase_channels',
              'former405_best_matching_rows', 'truth_min_rounding_boundary_margin_channels',
              'nearest_cartesian_continuum_max_error_channels', 'drift_projection_delta_hz_s', 'phase_projection_channels',
              'drift_interval_at_truth_phase', 'phase_interval_at_truth_drift_channels']
    with (out / 'DIAGNOSIS19.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for r in reports:
            writer.writerow({field: json.dumps(r[field], sort_keys=True, separators=(',', ':')) if isinstance(r[field], (dict, list)) else r[field] for field in fields})
    (out / 'METHOD.md').write_text(METHOD)
    for pin in params['input_pins']:
        require(sha(root / pin['path']) == pin['sha256'], 'An original input changed during diagnosis')
    usage = resource.getrusage(resource.RUSAGE_SELF)
    receipt = {'status': result['status'], 'CPU_seconds': time.process_time() - before_cpu,
               'wall_seconds': time.monotonic() - before_wall, 'peak_RSS_bytes': usage.ru_maxrss * 1024,
               'params_sha256': args.params_sha256, 'code_sha256': args.code_sha256,
               'input_pins_reverified': len(params['input_pins']),
               'NPZ_members_decoded': params['read_NPZ_fields'], 'observed_score_members_decoded': False,
               'original_input_arrays_unchanged': True, 'numeric_model': params['geometry']['model'],
               'outputs': [{'path': str(p.relative_to(root)), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(out.iterdir())]}
    require(sum(p.stat().st_size for p in out.iterdir()) < params['output_bytes_cap'], 'Output budget exceeded')
    (out / 'EXECUTION_RECEIPT.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'diagnoses'}, sort_keys=True))


if __name__ == '__main__':
    main()
