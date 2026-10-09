"""New reciprocal OFF-as-target diagnostic on an already opened six-scan cache.

Uses native correlated spectra, freezes the whole selection family, and retains
full signed results. This is a control diagnostic, never a sky false-alarm test.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import time

for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'

SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ON = SCANS[::2]
OFF = SCANS[1::2]
REVERSE = {'epoch1_off': ('epoch1_on', 'epoch2_on'),
           'epoch2_off': ('epoch2_on', 'epoch3_on'),
           'epoch3_off': ('epoch3_on',)}
CONTROLS_COUNT = {'epoch1_on': 1, 'epoch2_on': 2, 'epoch3_on': 2,
                  'epoch1_off': 2, 'epoch2_off': 2, 'epoch3_off': 1}
C0, N, EDGE, HALO, ROWS, PATCH = 159383552, 1048576, 283, 32, 16, 64
DF, F0, TSAMP = -2.835503418452676, 1876464843.75, 17.986224128


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def frequency(index):
    return F0 + DF * (C0 + int(index))


def mean_width(x, w):
    if w == 1:
        return x
    p = np.pad(x, 1, mode='edge')
    return (p[:-2] + p[1:-1] + p[2:]) / 3


def peaks(scan, maximum, winner):
    eligible = np.arange(EDGE, N - EDGE)
    order = eligible[np.lexsort((eligible, -maximum[eligible]))]
    chosen, records = [], []
    for k in order:
        k = int(k)
        if any(abs(k - j) <= HALO for j in chosen):
            continue
        chosen.append(k)
        records.append({'id': f'{scan}_reciprocal_rank_{len(chosen):02}',
                        'originating_scan': scan, 'source_channel': C0 + k,
                        'frequency_hz': frequency(k), 'width_channels': int(winner[k]),
                        'contrast': float(maximum[k]), 'adjacent_target_controls': list(REVERSE[scan])})
        if len(chosen) == 20:
            break
    return records


def run(args):
    scope = json.loads(Path(args.scope).read_text())
    if sha(__file__) != scope['script_sha256']:
        raise ValueError('Code differs from the frozen scope')
    fixed = {'channels': [C0, C0 + N], 'eligible_local_indices': [EDGE, N - EDGE],
             'reverse_mapping': {k: list(v) for k, v in REVERSE.items()},
             'widths_channels': [1, 3], 'halo_channels': HALO, 'top_per_control_scan': 20,
             'time_review_top_per_control_scan': 3, 'time_rows': ROWS, 'time_patch_halfwidth': PATCH,
             'row_background_exclusion_halfwidth': 3, 'CPU_cap_s': 150, 'wall_cap_s': 300,
             'memory_cap_bytes': 1610612736, 'new_telescope_requests': 0}
    if any(scope.get(k) != v for k, v in fixed.items()):
        raise ValueError('Frozen scope and implemented constants differ')
    for pin in scope['inputs']:
        p = Path(args.workspace) / pin['path']
        if p.stat().st_size != pin['bytes'] or sha(p) != pin['sha256']:
            raise ValueError(f'Input pin mismatch: {pin["path"]}')
    source = json.loads((Path(args.workspace) / scope['source_manifest']).read_text())
    if [s['label'] for s in source['sources']] != list(SCANS):
        raise ValueError('Source scan identity/order mismatch')
    for item in source['sources']:
        a = item['current_header']['data_attributes']
        if abs(a['fch1'] * 1e6 - F0) > 1e-6 or abs(a['foff'] * 1e6 - DF) > 1e-12:
            raise ValueError('Source frequency grid mismatch')
    out = Path(args.outdir)
    smooth = {1: {}, 3: {}}
    for scan in SCANS:
        with np.load(Path(args.spectra_dir) / f'{scan}_full_chunk_spectrum.npz', allow_pickle=False) as z:
            if int(z['source_channel0']) != C0 or int(z['source_channel_count']) != N:
                raise ValueError('Saved spectrum grid mismatch')
            m = np.asarray(z['row_normalized_mean_power'], dtype=np.float64)
            b = np.asarray(z['running_median_baseline'], dtype=np.float64)
            if m.shape != (N,) or b.shape != (N,) or not np.isfinite(m).all() or not np.isfinite(b).all() or (b <= 0).any():
                raise ValueError('Invalid saved native spectrum')
            x = m / b - 1
        for w in (1, 3):
            smooth[w][scan] = mean_width(x, w)
    envelope = {w: {s: maximum_filter1d(smooth[w][s], size=2 * HALO + 1, mode='nearest')
                    for s in ON} for w in (1, 3)}
    maxima, summaries, ranked = {}, {}, {}
    # Original ON arrays are read, never recomputed. Only reciprocal OFF scores
    # are new, with the identical widths, channel family and control envelope.
    for scan in ON:
        with np.load(Path(args.original_dir) / f'{scan}_full_chunk_stationary_contrast.npz', allow_pickle=False) as z:
            if int(z['source_channel0']) != C0 or int(z['source_channel_count']) != N:
                raise ValueError('Saved original contrast grid mismatch')
            maxima[scan] = np.array(z['maxD'], dtype=np.float64)
    for scan in OFF:
        scores = {}
        for w in (1, 3):
            control = np.maximum.reduce([envelope[w][s] for s in REVERSE[scan]])
            scores[w] = smooth[w][scan] - control
        maximum = np.maximum(scores[1], scores[3])
        winner = np.where(scores[3] > scores[1], 3, 1).astype(np.uint8)
        if not np.isfinite(maximum).all():
            raise ValueError('Invalid reciprocal contrast')
        maxima[scan] = maximum
        np.savez_compressed(out / f'{scan}_reciprocal_contrast.npz', D1=scores[1], D3=scores[3],
                            maxD=maximum, winning_width=winner, source_channel0=C0,
                            source_channel_count=N, eligible_local_index0=EDGE,
                            eligible_local_index_stop=N - EDGE, df_hz=DF, fch1_hz=F0)
        ranked[scan] = peaks(scan, maximum, winner)
        print('NEW_RECIPROCAL_CONTROL_COMPLETE', scan, ranked[scan][0]['contrast'], flush=True)
    for scan in SCANS:
        x = maxima[scan][EDGE:N - EDGE]
        if x.shape != (N - 2 * EDGE,) or not np.isfinite(x).all():
            raise ValueError('Invalid eligible score array')
        k = int(np.argmax(x)) + EDGE
        summaries[scan] = {'role': 'original_target_saved' if scan in ON else 'new_reciprocal_control',
                           'eligible_carriers': len(x), 'adjacent_control_scans': CONTROLS_COUNT[scan],
                           'positive_contrast_channels': int((x > 0).sum()), 'maximum_contrast': float(x.max()),
                           'maximum_frequency_hz': frequency(k), 'maximum_source_channel': C0 + k}
    selected_on = json.loads((Path(args.workspace) / scope['selected_original_profiles']).read_text())
    thresholds = []
    for record in selected_on:
        value = record['signed_contrast_fractional_units']
        ncontrol = CONTROLS_COUNT[record['originating_on']]
        scan_counts = {s: int((maxima[s][EDGE:N - EDGE] >= value).sum()) for s in SCANS}
        thresholds.append({'original_id': record['ranked_id'], 'contrast_threshold': value,
                           'original_adjacent_control_count': ncontrol,
                           'per_scan_channels_at_or_above_threshold': scan_counts,
                           'reciprocal_scans_with_equal_control_count': [s for s in OFF if CONTROLS_COUNT[s] == ncontrol],
                           'unit': 'correlated carrier channels; not independent peaks or probability'})
    review = [r for scan in OFF for r in ranked[scan][:3]]
    raw = np.empty((len(review), 6, ROWS, 2 * PATCH + 1), dtype=np.float32)
    for sindex, scan in enumerate(SCANS):
        with h5py.File(Path(args.cache_dir) / f'{scan}.compact.h5', 'r', rdcc_nbytes=80 * 1024**2, rdcc_nslots=521, rdcc_w0=0.0) as h:
            data = h['data']
            if data.shape != (ROWS, 1, N) or data.dtype != np.dtype('float32') or data.chunks != (1, 1, N):
                raise ValueError('Cached power dimensions differ')
            for case, r in enumerate(review):
                k = r['source_channel'] - C0
                raw[case, sindex] = data[:, 0, k - PATCH:k + PATCH + 1]
        print('NEW_CONTROL_PATCHES_READ', scan, len(review), flush=True)
    if not np.isfinite(raw).all() or (raw < 0).any():
        raise ValueError('Invalid native control patches')
    medians_data = json.loads((Path(args.workspace) / scope['normalization']).read_text())['row_medians_over_full_physical_chunk']
    medians = np.asarray([medians_data[s] for s in SCANS], dtype=np.float64)
    if medians.shape != (6, ROWS) or not np.isfinite(medians).all() or (medians <= 0).any():
        raise ValueError('Invalid preserved row normalization')
    norm = raw / medians[None, :, :, None]
    flanks = np.abs(np.arange(-PATCH, PATCH + 1)) > 3
    backgrounds = np.median(norm[:, :, :, flanks], axis=-1)
    timelines = []
    for case, r in enumerate(review):
        w = r['width_channels']; half = w // 2
        centers = norm[case, :, :, PATCH - half:PATCH + half + 1].mean(axis=-1)
        residual = centers - backgrounds[case]
        item = dict(r)
        item['by_scan'] = {s: {'residual_each_row': residual[j].tolist(),
                              'positive_rows': int((residual[j] > 0).sum()),
                              'mean_residual': float(residual[j].mean()),
                              'median_residual': float(np.median(residual[j]))} for j, s in enumerate(SCANS)}
        timelines.append(item)
        np.savez_compressed(out / f'{r["id"]}_fixed_patch.npz', raw_power=raw[case],
                            row_normalized_power=norm[case], residual_each_row=residual,
                            selected_width_channels=w, saved_full_chunk_row_medians=medians,
                            source_channel=r['source_channel'], scan_labels=np.asarray(SCANS))
    old_time = json.loads((Path(args.workspace) / scope['original_time_review']).read_text())
    write(out / 'RECIPROCAL_TOP20.json', ranked)
    write(out / 'CONTROL_TIME_REVIEW.json', timelines)
    result = {'scope': 'EXPLORATORY_NATIVE_RECIPROCAL_CONTROL_DIAGNOSTIC', 'scan_summary': summaries,
              'original_seven_threshold_comparison': thresholds,
              'new_control_profiles_reviewed': len(timelines), 'new_raw_powers_retained': int(raw.size),
              'new_control_widths': [r['width_channels'] for r in review],
              'original_seven_time_profiles_used_as_saved_context_count': len(old_time),
              'reverse_mapping': {k: list(v) for k, v in REVERSE.items()},
              'calibrated_probability_or_sky_false_alarm_rate': False,
              'independent_visits': 1, 'new_observation_exposure_s': 0,
              'original_seven_dispositions': 'UNRESOLVED_UNCHANGED', 'qualification': 'A_B_FAIL_CLOSED_UNCHANGED',
              'limitations': ['Same six scans and historical visit; no independent confirmation',
                              'OFF spectra may contain variable RFI, instrument response and celestial backgrounds; they are not certified nulls',
                              'Targets and controls are not assumed exchangeable; no permutation p-value or calibrated FAP',
                              'Boundary scans have one adjacent control, interior scans two; compare equal counts explicitly',
                              'Counts across channels and widths are correlated; NMS top20 is descriptive',
                              'A similar control elsewhere does not veto the original frequency or establish its origin',
                              'No original stationary search, drift scoring, old validation or holdout reopening']}
    write(out / 'NATIVE_CONTROL_RESULT.json', result)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), constrained_layout=True)
    x = np.arange(6)
    axes[0].bar(x, [summaries[s]['maximum_contrast'] for s in SCANS],
                color=['#1763a6' if s in ON else '#b46116' for s in SCANS])
    axes[0].set_xticks(x, ['ON1 (1)', 'OFF1 (2)', 'ON2 (2)', 'OFF2 (2)', 'ON3 (2)', 'OFF3 (1)'], rotation=30)
    axes[0].set_ylabel('Largest signed spectral contrast')
    axes[0].set_title('Whole-band selected maxima\nParentheses: number of adjacent controls')
    axes[0].grid(axis='y', alpha=.2)
    axes[1].scatter(range(1, 10), [r['by_scan'][r['originating_scan']]['positive_rows'] for r in timelines], color='#b46116', s=45)
    axes[1].set_ylim(-.5, 16.5); axes[1].set_yticks([0, 4, 8, 12, 16]); axes[1].set_xticks(range(1, 10))
    axes[1].set_xlabel('Reciprocal OFF profile: ranks 1–3 in OFF1 / OFF2 / OFF3')
    axes[1].set_ylabel('Positive rows out of 16')
    axes[1].set_title('New data-selected control time profiles\nFixed center/width; all integrations retained')
    axes[1].grid(alpha=.2)
    fig.suptitle('Native control diagnostic — one visit, correlated selection, no calibrated probability', fontsize=11)
    fig.savefig(out / 'native_control_overview.png', dpi=150)
    plt.close(fig)
    outputs = [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(out.iterdir()) if p.is_file()]
    receipt = {'status': 'COMPLETE_NEW_RECIPROCAL_CONTROL_DIAGNOSTIC', 'script_sha256': sha(__file__),
               'scope_sha256': sha(args.scope), 'verified_inputs': scope['inputs'], 'outputs': outputs,
               'eligible_carriers_per_scan': N - 2 * EDGE, 'same_existing_bandwidth_hz': (N - 2 * EDGE) * abs(DF),
               'new_control_scan_searches': 3, 'new_control_width_hypotheses_per_scan': 2 * (N - 2 * EDGE),
               'new_control_time_profiles': len(timelines), 'new_raw_powers_retained': int(raw.size),
               'new_telescope_GETs': 0, 'new_telescope_source_bytes': 0,
               'new_drift_searches': 0, 'new_qualification_trials': 0,
               'process_CPU_s_including_imports': time.process_time(), 'wall_s_including_imports': time.monotonic() - START,
               'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
               'whole_activity_CPU_s': None, 'conservative_activity_reservation_CPU_s': 200}
    write(out / 'ANALYSIS_RECEIPT.json', receipt)
    print(json.dumps({k: receipt[k] for k in ('status', 'process_CPU_s_including_imports', 'wall_s_including_imports', 'peak_RSS_bytes')}), flush=True)


if __name__ == '__main__':
    START = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('scope', 'workspace', 'spectra-dir', 'original-dir', 'cache-dir', 'outdir'):
        parser.add_argument('--' + key, required=True)
    args = parser.parse_args()
    Path(args.outdir).mkdir(parents=True, exist_ok=False)
    def deadline(signum, frame):
        raise TimeoutError('Frozen job limit reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (150, 151))
    resource.setrlimit(resource.RLIMIT_AS, (1610612736, 1610612736))
    signal.alarm(300)
    try:
        import numpy as np
        import h5py
        import hdf5plugin
        from scipy.ndimage import maximum_filter1d
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        run(args)
    except BaseException as exc:
        write(Path(args.outdir) / 'FAILURE.json', {'status': 'FAILED_CLOSED_NEW_CONTROL_JOB',
                                                'error_type': type(exc).__name__, 'error': str(exc),
                                                'process_CPU_s': time.process_time(),
                                                'wall_s': time.monotonic() - START, 'retry_authorized': False})
        raise
    finally:
        signal.alarm(0)
