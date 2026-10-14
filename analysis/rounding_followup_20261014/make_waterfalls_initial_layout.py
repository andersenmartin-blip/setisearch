"""Render the fourteen frozen residual waterfalls after root GO and numerical QA.

This is a PNG-only presentation consumer, not a detector or a score search.
Every display cell uses a direct, centered median of 501 native raw channels
from its authenticated raw12096 crop and the unchanged saved row normalizers.
The old four-row query and exact best four-row query are read from pinned JSON.
No fitted drift is inferred, no hypothesis is selected here, and raw128 crops
and all numerical producer/QA artifacts are never modified.

The required rendering GO has schema SETI_RESIDUAL_WATERFALL_GO_V1, status
GO_RESIDUAL_WATERFALLS_AFTER_NUMERICAL_QA, root_static_review PASS, source_root,
observed_score_execution_complete true, numerical_qa_complete true, profile_ids,
and file declarations (path/bytes/sha256) for script, scope, matrix, profiles,
numerical_qa. It also records the exact approved observed_status and qa_status.
All declared paths are relative to --workspace-root. The source root is the
workspace's existing seti_work directory. See REQUIRED_RENDERING in this file.

--check-only authenticates JSON and file bytes, never opens spectral NPZ arrays
or imports NumPy/Matplotlib. Actual rendering additionally needs the complete
root GO and a passing numerical QA receipt before either library is imported.
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
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'

SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
STRONGEST_ORIGIN = 'epoch3_on_rank1'
OWN_PROFILE_IDS = tuple(f'epoch{e}_on_rank{r}_epoch{e}_on' for e in (1, 2, 3) for r in (1, 2, 3))
STRONGEST_PROFILE_IDS = tuple(f'{STRONGEST_ORIGIN}_{scan}' for scan in SCANS)
PROFILE_IDS = OWN_PROFILE_IDS + tuple(p for p in STRONGEST_PROFILE_IDS if p not in OWN_PROFILE_IDS)
REQUIRED_RENDERING = {
    'profile_count': 14, 'rows': 16, 'columns': 49, 'native_channel_half_width': 24,
    'median_width': 501, 'fixed_z_clip': [-5, 5], 'raw_crop_columns': 12096,
    'normalization_reused_without_modification': True,
    'row_reference': 'original_coarse_per_row_rounded_native_channel',
    'overlay': 'old_original_selected4_and_zero_offset_exact_max7_selected4',
    'selection': 'nine_own_ON_profiles_union_six_epoch3_on_rank1_contexts',
    'figure_inches': [8.6, 3.2], 'dpi': 200, 'output_format': 'PNG_ONLY',
    'new_scores_or_hypothesis_selection': False,
}
NORM_FIELDS = ('row_power_median', 'row_residual_median', 'row_residual_MAD_scale',
               'row_winsorized_residual_location')
CPU_CAP, WALL_CAP, MEMORY_CAP = 120, 180, 1024 ** 3


def require(condition, message):
    if not condition:
        raise ValueError(message)


def no_duplicate_keys(items):
    result = {}
    for key, value in items:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_bytes(), object_pairs_hook=no_duplicate_keys,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Nonfinite JSON: ' + v)))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def confined(root, name):
    relative = Path(name)
    candidate = root / relative
    require(not relative.is_absolute() and '..' not in relative.parts and
            candidate.resolve().is_relative_to(root) and not candidate.is_symlink(),
            'Input must be confined to the declared read-only root: ' + str(name))
    return candidate


def authenticate(root, declaration):
    require(isinstance(declaration, dict) and set(declaration) >= {'path', 'bytes', 'sha256'},
            'Expected a file declaration with path/bytes/sha256')
    path = confined(root, declaration['path'])
    require(path.is_file() and path.stat().st_size == declaration['bytes'] and
            sha256(path) == declaration['sha256'], 'File pin differs: ' + declaration['path'])
    return path


def pin(path, root):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha256(path)}


def index_profiles(document):
    values = document['profiles']
    require(isinstance(values, list) and len(values) == 54, 'Expected all 54 validated context profiles')
    indexed = {p['profile_id']: p for p in values}
    require(len(indexed) == 54, 'Duplicate context profile IDs')
    return indexed


def integer_list(value, count, label):
    require(isinstance(value, list) and len(value) == count and all(type(v) is int for v in value),
            label + ' must contain exactly ' + str(count) + ' native integers')
    return value


def validate(args):
    workspace = Path(args.workspace_root).resolve()
    go_path = Path(args.go).resolve()
    require(go_path.is_relative_to(workspace) and not go_path.is_symlink(), 'Rendering GO outside workspace')
    go = read_json(go_path)
    require(go['schema'] == 'SETI_RESIDUAL_WATERFALL_GO_V1' and
            go['status'] == 'GO_RESIDUAL_WATERFALLS_AFTER_NUMERICAL_QA' and
            go['root_static_review'] == 'PASS' and
            go['observed_score_execution_complete'] is True and go['numerical_qa_complete'] is True,
            'Completed root rendering GO and numerical QA are required')
    require(go['rendering'] == REQUIRED_RENDERING and go['profile_ids'] == list(PROFILE_IDS),
            'Frozen fourteen-profile rendering scope differs')
    source_root = Path(go['source_root']).resolve()
    require(source_root == workspace / 'seti_work', 'Only the existing seti_work input root is authorized')
    paths = {name: authenticate(workspace, go[name]) for name in
             ('script', 'scope', 'matrix', 'profiles', 'numerical_qa')}
    require(paths['script'] == Path(__file__).resolve(), 'Rendering GO does not pin this script')
    require(paths['scope'] == workspace / 'rounding_followup/SCOPE.json', 'Unexpected observed scope')
    require(paths['matrix'] == source_root / 'seti_burst_full/context_results/CONTEXT_PROFILES.json',
            'Only the saved fixed context matrix is authorized')
    require(paths['profiles'].parent.is_relative_to(workspace / 'rounding_followup') and
            paths['numerical_qa'].parent.is_relative_to(workspace / 'rounding_followup'),
            'Observed results and completed numerical QA must belong to this follow-up')
    scope, matrix, observed, qa = (read_json(paths[name]) for name in
                                   ('scope', 'matrix', 'profiles', 'numerical_qa'))
    require(scope['waterfall_selection'] == list(PROFILE_IDS),
            'Root scope must authorize exactly the fourteen predetermined profiles in order')
    waterfall_scope = scope['waterfall']
    require(waterfall_scope['row_count'] == 16 and
            waterfall_scope['channel_offsets'] == list(range(-24, 25)) and
            waterfall_scope['color_z_bounds'] == [-5, 5] and
            waterfall_scope['strongest_prior_track'] == STRONGEST_ORIGIN,
            'Root scope waterfall rows, native-channel offsets, color bounds or prior track differ')
    scope_hash = sha256(paths['scope'])
    require(observed['scope_sha256'] == scope_hash and observed['status'] == go['observed_status'] and
            observed['status'].startswith('COMPLETE'), 'Observed execution is incomplete or has another scope')
    require(qa['status'] == go['qa_status'] and qa['status'].startswith('PASS') and
            'NUMERICAL' in qa['status'].upper() and qa['scope_sha256'] == scope_hash,
            'A passing, completed numerical QA receipt for this exact scope is required')
    require(matrix['status'] == 'COMPLETE_FULL_ON_BURST4_CLEAN_TOP9_FIXED_TRACKS54_SIX_SCAN_CONTEXTS',
            'Saved matrix completion status differs')
    metadata, results = index_profiles(matrix), index_profiles(observed)
    require(set(metadata) == set(results), 'Observed and saved profile census differ')
    require(scope['profile_ids'] == [p['profile_id'] for p in matrix['profiles']],
            'Root frozen profile order differs from saved matrix')
    selected = []
    for profile_id in PROFILE_IDS:
        original, result = metadata[profile_id], results[profile_id]
        track = original['selected_track']
        require(result['context_scan_id'] == original['context_scan_id'] and
                result['origin_scan_id'] == track['scan_id'] and result['origin_rank'] == track['rank'] and
                result['times_from_primary_reference_s'] == original['times_from_primary_reference_s'],
                'Result origin, scan, rank or time provenance differs: ' + profile_id)
        coarse = integer_list(result['coarse_zero_offset_full16_absolute_centers'], 16, 'Coarse full16 reference')
        require(coarse == original['rounded_absolute_centers'], 'Saved original coarse native reference differs')
        old_rows = integer_list(original['window_source_rows'], 4, 'Original selected source rows')
        require(old_rows == list(range(track['window_start_row'], track['window_start_row'] + 4)) and
                track['width_channels'] == 1, 'Original selected four-row width1 query differs')
        offset = result['offset_results'][0]
        require(offset['offset_channels'] == 0, 'Target result must be zero-offset')
        winner = offset['exact_max7']
        new_rows = integer_list(winner['window_source_rows'], 4, 'Exact selected source rows')
        new_channels = integer_list(winner['selected4_absolute_centers'], 4, 'Exact selected native centers')
        require(new_rows == list(range(winner['window_start_row'], winner['window_start_row'] + 4)) and
                winner['window_start_row'] in (0, 2, 4, 6, 8, 10, 12), 'Exact selected window differs')
        require(all(abs(channel - coarse[row]) <= 24 for row, channel in zip(new_rows, new_channels)),
                'Exact selected native cells outside the fixed display; do not silently clip them')
        require(math.isfinite(winner['score']) and math.isfinite(original['fixed_four_row_score']),
                'Nonfinite saved annotation score')
        raw_decl, norm_decl = original['raw_normalization_crop'], original['normalization']
        require(raw_decl['path'].endswith('_raw12096.npz') and 'raw128' not in raw_decl['path'],
                'Only the unchanged raw12096 normalization crop may be opened')
        raw_path, norm_path = authenticate(source_root, raw_decl), authenticate(source_root, norm_decl)
        normal = read_json(norm_path)
        require(set(normal) == set(NORM_FIELDS) | {'normalization_unmasked_counts', 'normalization_source_channels'},
                'Saved normalization schema differs')
        for field in NORM_FIELDS:
            require(len(normal[field]) == 16 and all(math.isfinite(x) for x in normal[field]),
                    'Saved row normalization field differs: ' + field)
        require(all(v > 0 for v in normal['row_power_median']) and
                all(v > 0 for v in normal['row_residual_MAD_scale']) and
                normal['normalization_unmasked_counts'] == [4096] * 16,
                'Saved positive row normalization and unchanged core are required')
        core = integer_list(normal['normalization_source_channels'], 4096, 'Original normalization core')
        require(core == list(range(core[0], core[0] + 4096)), 'Original normalization core is not contiguous')
        source_channel0 = core[0] - 4000
        require(min(coarse) - 24 - 250 >= source_channel0 and
                max(coarse) + 24 + 250 < source_channel0 + 12096,
                'Displayed median501 cells exceed saved raw12096 support')
        selected.append({'profile_id': profile_id, 'original': original, 'result': result, 'winner': winner,
                         'raw_path': raw_path, 'normal': normal, 'source_channel0': source_channel0})
    return workspace, source_root, go_path, go, paths, selected


def residual_grid(item, np):
    """Compute display residuals only, never a summed four-row score."""
    with np.load(item['raw_path'], allow_pickle=False) as capsule:
        require(set(capsule.files) == {'raw_power', 'source_channel0', 'normalization_source_channels',
                                       'absolute_time_rows'}, 'Saved raw12096 NPZ members differ')
        raw = capsule['raw_power']
        require(raw.shape == (16, 12096) and raw.dtype == np.dtype('<f4') and np.isfinite(raw).all(),
                'Saved raw12096 data shape/dtype/finiteness differs')
        require(capsule['source_channel0'].shape == () and capsule['source_channel0'].dtype == np.dtype('<i8') and
                int(capsule['source_channel0']) == item['source_channel0'] and
                np.array_equal(capsule['absolute_time_rows'], np.arange(16, dtype=np.int64)) and
                np.array_equal(capsule['normalization_source_channels'],
                               np.asarray(item['normal']['normalization_source_channels'], dtype=np.int64)),
                'Saved raw12096 origin, source rows or unchanged normalization core differ')
        coarse = np.asarray(item['result']['coarse_zero_offset_full16_absolute_centers'], dtype=np.int64)
        source_channels = coarse[:, None] + np.arange(-24, 25, dtype=np.int64)[None, :]
        local = source_channels - item['source_channel0']
        require(local.min() >= 250 and local.max() + 250 < 12096, 'Direct median501 support outside crop')
        normal = item['normal']
        z = np.empty((16, 49), dtype=np.float64)
        for row in range(16):
            ratio = raw[row].astype(np.float64) / normal['row_power_median'][row]
            # Every displayed cell receives its own complete direct native501 median.
            medians = np.asarray([np.median(ratio[c - 250:c + 251]) for c in local[row]], dtype=np.float64)
            z[row] = (ratio[local[row]] - medians - normal['row_winsorized_residual_location'][row]) / normal['row_residual_MAD_scale'][row]
        require(np.isfinite(z).all(), 'Nonfinite displayed standardized residuals')
        return z, source_channels


def render_one(item, z, output_path, plt, np):
    original, result, winner = item['original'], item['result'], item['winner']
    coarse = np.asarray(result['coarse_zero_offset_full16_absolute_centers'], dtype=np.int64)
    old_rows = np.asarray(original['window_source_rows'], dtype=np.int64)
    new_rows = np.asarray(winner['window_source_rows'], dtype=np.int64)
    new_channels = np.asarray(winner['selected4_absolute_centers'], dtype=np.int64)
    fig = plt.figure(figsize=(8.6, 3.2), dpi=200)
    ax = fig.add_axes([0.175, 0.265, 0.735, 0.55])
    cax = fig.add_axes([0.927, 0.265, 0.018, 0.55])
    image = ax.imshow(z, origin='lower', interpolation='nearest', aspect='auto',
                      extent=(-24.5, 24.5, -0.5, 15.5), cmap='RdBu_r', vmin=-5, vmax=5)
    ax.axvline(0, color='black', alpha=0.22, linewidth=0.6)
    ax.scatter(np.zeros(4), old_rows, marker='s', s=62, facecolors='none', edgecolors='#00bdd2',
               linewidths=1.8, label='Original selected 4', zorder=3)
    ax.scatter(new_channels - coarse[new_rows], new_rows, marker='o', s=23, facecolors='#ffd629',
               edgecolors='#2d1552', linewidths=0.75, label='Exact best selected 4', zorder=4)
    ax.set_xlim(-24.5, 24.5); ax.set_ylim(-0.5, 15.5)
    ax.set_xticks([-24, -16, -8, 0, 8, 16, 24])
    ax.set_yticks(range(16))
    times = original['times_from_primary_reference_s']
    ax.set_yticklabels([f'{row:02d} / {times[row]:+.1f}' for row in range(16)], fontsize=6.8)
    ax.tick_params(axis='x', labelsize=8, length=3)
    ax.tick_params(axis='y', length=2, pad=3)
    ax.set_ylabel('Source row / seconds\nfrom origin reference', fontsize=8, labelpad=7)
    ax.set_xlabel('Native-channel offset from the original coarse reference of each row', fontsize=8, labelpad=4)
    bar = fig.colorbar(image, cax=cax, ticks=[-5, 0, 5]); bar.ax.tick_params(labelsize=7, length=2)
    bar.set_label('Residual z (fixed clip)', fontsize=7, labelpad=3)
    origin = result['origin_scan_id'].replace('_', ' ').upper()
    context = original['context_scan_id'].replace('_', ' ').upper()
    fig.text(0.175, 0.945, f'{origin} rank {result["origin_rank"]}  →  {context} · {original["context_target"]}',
             fontsize=10.5, weight='bold', ha='left', va='top')
    fig.text(0.175, 0.874, f'Saved coarse 4-row Z = {original["fixed_four_row_score"]:.3f}   |   '
             f'Saved exact max-7 Z = {winner["score"]:.3f}   |   post hoc local selection',
             fontsize=8.2, ha='left', va='top')
    ax.legend(loc='upper left', bbox_to_anchor=(0.0, -0.34), frameon=False, ncol=2,
              fontsize=7.5, handlelength=1.5, columnspacing=2.0, borderaxespad=0)
    fig.text(0.175, 0.045, f'Row-dependent native reference: c(0)={int(coarse[0])}; c(15)={int(coarse[15])}. '
             'Direct median501; unchanged normalization.\n'
             'Exact markers are saved native cells, not a unique physical drift fit. Z is descriptive; no calibrated FAP or detection.',
             fontsize=6.6, ha='left', va='bottom')
    fig.savefig(output_path, dpi=200, facecolor='white', metadata={'Software': 'SETI frozen residual waterfall consumer v1'})
    plt.close(fig)


def create_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace-root', required=True)
    parser.add_argument('--go', required=True, help='Separate root-authored rendering GO')
    parser.add_argument('--output-dir', help='Fresh PNG-only output directory outside seti_work')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    workspace, source_root, go_path, go, paths, selected = validate(args)
    if args.check_only:
        print(json.dumps({'status': 'PASS_PINNED_WATERFALL_METADATA_AND_COMPLETED_NUMERICAL_QA',
                          'profiles': len(selected), 'raw_arrays_opened': False, 'new_scores_computed': False,
                          'numpy_imported': False, 'PDF_generated': False}))
        return
    require(args.output_dir, 'Fresh output directory is required')
    output = Path(args.output_dir).resolve()
    require(not output.exists() and output.is_relative_to(workspace) and not output.is_relative_to(source_root),
            'Output must be a fresh workspace directory outside the read-only source root')
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Waterfall wall budget exceeded')))
    signal.alarm(WALL_CAP)
    started = time.monotonic()
    import numpy as np
    import matplotlib
    matplotlib.use('Agg', force=True)
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'axes.unicode_minus': True,
                         'text.usetex': False, 'figure.autolayout': False})
    output.mkdir(parents=True)
    plots = []
    for item in selected:
        z, source_channels = residual_grid(item, np)
        path = output / (item['profile_id'] + '_residual_waterfall.png')
        render_one(item, z, path, plt, np)
        original, result, winner = item['original'], item['result'], item['winner']
        plots.append({'profile_id': item['profile_id'], 'image': pin(path, workspace),
                      'context_scan_id': original['context_scan_id'],
                      'origin_scan_id': result['origin_scan_id'], 'origin_rank': result['origin_rank'],
                      'input_raw12096': original['raw_normalization_crop'],
                      'input_unchanged_normalization': original['normalization'],
                      'coarse_row_reference_native_channels': result['coarse_zero_offset_full16_absolute_centers'],
                      'source_rows': list(range(16)), 'times_from_primary_reference_s': original['times_from_primary_reference_s'],
                      'display_native_channel_offsets': list(range(-24, 25)),
                      'display_native_source_channel_intervals_inclusive': source_channels[:, [0, -1]].tolist(),
                      'old_selected4_source_rows': original['window_source_rows'],
                      'old_selected4_native_channels': [result['coarse_zero_offset_full16_absolute_centers'][row]
                                                       for row in original['window_source_rows']],
                      'exact_best_selected4_source_rows': winner['window_source_rows'],
                      'exact_best_selected4_native_channels': winner['selected4_absolute_centers'],
                      'saved_original4_score': original['fixed_four_row_score'],
                      'saved_exact_max7_score': winner['score'],
                      'exact_witness_is_not_unique_physical_drift_fit': True})
        print(json.dumps({'rendered_profile': item['profile_id'], 'PNG': path.name}), flush=True)
    require(len(plots) == 14, 'Exactly fourteen PNG waterfalls are required')
    usage = resource.getrusage(resource.RUSAGE_SELF)
    manifest = {'schema': 'SETI_FROZEN_RESIDUAL_WATERFALLS_V1',
                'status': 'COMPLETE_FOURTEEN_PINNED_RESIDUAL_WATERFALLS_AFTER_NUMERICAL_QA',
                'root_GO': pin(go_path, workspace), 'script': pin(Path(__file__).resolve(), workspace),
                'scope': go['scope'], 'matrix': go['matrix'], 'profiles': go['profiles'],
                'numerical_qa': go['numerical_qa'], 'rendering': REQUIRED_RENDERING,
                'profile_ids': list(PROFILE_IDS), 'strongest_track_six_scan_order': list(STRONGEST_PROFILE_IDS),
                'counts': {'profiles': 14, 'PNG_files': 14, 'display_cells': 14 * 16 * 49,
                           'direct_native501_medians': 14 * 16 * 49, 'PDF_files': 0,
                           'new_scores_computed': 0, 'hypotheses_selected': 0},
                'posthoc_selection': True, 'qualified_SETI_detection': False, 'calibrated_FAP': False,
                'raw128_crops_opened': False, 'input_arrays_modified': False,
                'resource_limits': {'CPU_s': CPU_CAP, 'wall_s': WALL_CAP, 'memory_bytes': MEMORY_CAP},
                'resource_usage': {'CPU_s': usage.ru_utime + usage.ru_stime,
                                   'wall_s': time.monotonic() - started, 'peak_RSS_bytes': usage.ru_maxrss * 1024},
                'plots': plots}
    create_json(output / 'PLOT_MANIFEST.json', manifest)
    signal.alarm(0)
    print(json.dumps({'status': manifest['status'], 'PNG_files': 14, 'PDF_files': 0,
                      'display_cells': 10976, 'resource_usage': manifest['resource_usage']}))


if __name__ == '__main__':
    main()
