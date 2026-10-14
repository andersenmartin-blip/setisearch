"""Metadata-only preparation of exact continuous native four-row path families.

Geometry opens authenticated JSON metadata only. Observed-score execution is
fail-closed until a separate root-frozen scope and code GO are provided.
"""
from __future__ import annotations
import argparse
import hashlib
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

import geometry

MATRIX = 'seti_burst_full/context_results/CONTEXT_PROFILES.json'
DF, TSAMP = -2.7939677238464355, 18.253611008
HALF_DRIFT = 4 / 158
OFFSETS = (0, -1024, -768, -512, -256, 256, 512, 768, 1024)
WINDOW_STARTS = (0, 2, 4, 6, 8, 10, 12)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def pin(path, root=None):
    return {'path': path.relative_to(root).as_posix() if root else str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def create_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n');stream.flush();os.fsync(stream.fileno())


def geometry_preflight(args):
    root, config_path = Path(args.root).resolve(), Path(args.geometry_config).resolve()
    config = read(config_path)
    matrix_path = root / config['matrix']['path']
    require(config['matrix']['path'] == MATRIX and matrix_path.stat().st_size == config['matrix']['bytes']
            and sha(matrix_path) == config['matrix']['sha256'], 'Frozen geometry matrix pin differs')
    require(config['df_hz'] == DF and config['tsamp_s'] == TSAMP and config['half_drift_hz_s'] == HALF_DRIFT
            and config['offset_channels'] == list(OFFSETS) and config['window_start_rows'] == list(WINDOW_STARTS)
            and config['phase_box_channels'] == [-.5, .5], 'Frozen geometry constants differ')
    require(sha(Path(__file__).resolve().parent / 'geometry.py') == config['geometry_code_sha256'], 'Exact geometry code pin differs')
    matrix = read(matrix_path)
    require(len(matrix['profiles']) == 54 and [p['profile_id'] for p in matrix['profiles']] == config['profile_ids'], 'Frozen profile order differs')
    out = Path(args.geometry_output_dir).resolve()
    require(not out.exists() and not out.is_relative_to(root), 'Fresh geometry output outside read-only input tree required')
    budget = config['budget'];caps = config['caps']
    resource.setrlimit(resource.RLIMIT_CPU, (budget['CPU_seconds'], budget['CPU_seconds']))
    resource.setrlimit(resource.RLIMIT_AS, (budget['memory_bytes'], budget['memory_bytes']))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Geometry wall budget exceeded')))
    signal.alarm(budget['wall_seconds'])
    started = time.monotonic()
    import numpy as np
    profiles, evaluated, path_count, missing_count = [], 0, 0, 0
    for pi, profile in enumerate(matrix['profiles']):
        track = profile['selected_track'];times = profile['times_from_primary_reference_s']
        require(track['width_channels'] == 1 and len(times) == 16, 'Expected width1 metadata geometry')
        d0, base = track['drift_hz_s'], track['source_reference_channel']
        drifts = d0 + np.linspace(-HALF_DRIFT, HALF_DRIFT, 81, dtype=np.float64)
        drift_axis = np.repeat(drifts, 5);phase_axis = np.tile(np.asarray([-.5, -.25, 0., .25, .5]), 81)
        legacy = np.rint(base + phase_axis[:, None] + drift_axis[:, None] * np.asarray(times)[None, :] / DF).astype(np.int64)
        windows = []
        for wi, start in enumerate(WINDOW_STARTS):
            rows = list(range(start, start + 4))
            family = geometry.enumerate_paths(base, d0, [times[r] for r in rows], DF, HALF_DRIFT,
                                              caps['total_witness_pairs'] - evaluated)
            require(family['unique_paths'] <= caps['unique_paths_per_window'], 'Per-window exact path cap exceeded')
            evaluated += family['witness_pairs_evaluated'];path_count += family['unique_paths']
            require(path_count <= caps['total_unique_paths'] and evaluated <= caps['total_witness_pairs'], 'Global exact geometry cap exceeded')
            exact_paths = {tuple(p['channels']) for p in family['paths']}
            legacy_paths = sorted({tuple(p) for p in legacy[:, rows].tolist()})
            missing = [list(path) for path in legacy_paths if path not in exact_paths]
            missing_count += len(missing)
            family.update(window_index=wi, window_start_row=start, window_source_rows=rows,
                          legacy_unique_paths=len(legacy_paths), legacy_paths_attainable_exact_count=len(legacy_paths) - len(missing),
                          legacy_only_float_paths=missing,
                          legacy_hypothesis_indices_with_infeasible_exact_paths=[hi for hi, path in enumerate(legacy[:, rows].tolist()) if tuple(path) not in exact_paths])
            windows.append(family)
        profiles.append({'profile_id': profile['profile_id'], 'origin_scan_id': track['scan_id'],
                         'context_scan_id': profile['context_scan_id'], 'origin_rank': track['rank'],
                         'source_reference_channel': base, 'original_drift_hz_s': d0,
                         'times_from_primary_reference_s': times, 'windows': windows})
        if (pi + 1) % 6 == 0:
            print(json.dumps({'geometry_profiles_completed': pi + 1, 'total_unique_paths': path_count,
                              'witness_pairs_evaluated': evaluated}), flush=True)
    out.mkdir(parents=True)
    result = {'schema': 'SETI_EXACT_CONTINUOUS_ROUNDING_FAMILIES_V1', 'status': 'COMPLETE_METADATA_ONLY_EXACT_GEOMETRY_54_PROFILES_378_WINDOWS',
              'config': pin(config_path), 'geometry_code': pin(Path(geometry.__file__).resolve()),
              'geometry_driver': pin(Path(__file__).resolve()), 'source_matrix': config['matrix'],
              'raw_spectral_arrays_opened': False, 'observed_scores_evaluated': False,
              'metadata_legacy_float_coordinates_evaluated': True,
              'path_order': 'window_start_row_slow_native_four_channel_tuple_lexicographic_fast',
              'offset_translation': 'all_even_offsets_preserve_absolute_channel_tie_parity',
              'exact_arithmetic': 'Fraction.from_float separately for d0, every saved time, DF, half_box; phasebox exact +/-1/2',
              'caps': caps, 'profiles': profiles,
              'counts': {'profiles': 54, 'windows': 378, 'offsets': 9, 'total_unique_paths_zero_offset': path_count,
                         'total_offset_path_scores': path_count * 9, 'witness_pairs_evaluated': evaluated,
                         'legacy_only_float_unique_paths_across_windows': missing_count}}
    create_json(out / 'GEOMETRY.json', result)
    usage = resource.getrusage(resource.RUSAGE_SELF)
    receipt = {'status': 'PASS_BOUNDED_METADATA_ONLY_CONTINUOUS_ROUNDING_GEOMETRY',
               'raw_spectral_arrays_opened': False, 'observed_scores_evaluated': False,
               'config': pin(config_path), 'geometry': pin(out / 'GEOMETRY.json'),
               'counts': result['counts'], 'resource_limits': budget,
               'resource_usage': {'CPU_s': usage.ru_utime + usage.ru_stime, 'wall_s': time.monotonic() - started,
                                  'peak_RSS_bytes': usage.ru_maxrss * 1024}}
    create_json(out / 'GEOMETRY_RECEIPT.json', receipt)
    signal.alarm(0)
    print(json.dumps({'status': receipt['status'], 'counts': result['counts'], 'resource_usage': receipt['resource_usage']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--geometry-preflight', action='store_true')
    parser.add_argument('--geometry-config')
    parser.add_argument('--geometry-output-dir')
    args = parser.parse_args()
    require(args.geometry_preflight and args.geometry_config and args.geometry_output_dir,
            'Observed execution not yet frozen; geometry-only interface required')
    geometry_preflight(args)


if __name__ == '__main__':
    main()
