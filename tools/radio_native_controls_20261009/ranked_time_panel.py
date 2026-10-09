"""Complete the fixed top20 time-profile panel in all six directional rankings.

Reuses sixteen exact existing profiles. Only the other 104 are measured; this
does not rerun the spectral search or calibrate a sky probability.
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
COUNTS = {'epoch1_on': 1, 'epoch2_on': 2, 'epoch3_on': 2, 'epoch1_off': 2, 'epoch2_off': 2, 'epoch3_off': 1}
C0, N, H, R = 159383552, 1048576, 64, 16


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def dump(p, x):
    with Path(p).open('x', encoding='utf-8') as f:
        json.dump(x, f, indent=2, allow_nan=False); f.write('\n')


def read(root, rel):
    return json.loads((root / rel).read_text())


def main(a):
    root, out = Path(a.workspace), Path(a.outdir)
    cfg = json.loads(Path(a.scope).read_text())
    if sha(__file__) != cfg['script_sha256']:
        raise ValueError('Frozen panel code mismatch')
    for key, expected in [('total_panel_profiles', 120), ('reused_profiles', 16), ('new_profiles', 104),
                          ('top_per_scan', 20), ('rows', R), ('patch_halfwidth', H),
                          ('background_exclusion_halfwidth', 3), ('CPU_cap_s', 90), ('wall_cap_s', 240),
                          ('positive_row_summary_cuts', [13, 15, 16]), ('memory_cap_bytes', 1610612736)]:
        if cfg[key] != expected:
            raise ValueError('Frozen panel constants mismatch')
    for pin in cfg['inputs']:
        p = root / pin['path']
        if p.stat().st_size != pin['bytes'] or sha(p) != pin['sha256']:
            raise ValueError('Frozen panel input mismatch: ' + pin['path'])
    original = read(root, cfg['original_ranks'])
    reciprocal = read(root, cfg['reciprocal_ranks'])
    records = []
    for s in SCANS:
        xs = original[s] if s.endswith('_on') else reciprocal[s]
        if len(xs) != 20:
            raise ValueError('Panel lacks exactly twenty ranks per scan')
        for rank, x in enumerate(xs, 1):
            if s.endswith('_on'):
                rec = {'id': x['ranked_id'], 'scan': s, 'rank': rank, 'source_channel': x['source_channel'],
                       'frequency_hz': x['frequency_hz'], 'width': x['winning_width_channels'],
                       'contrast': x['signed_contrast_fractional_units']}
            else:
                rec = {'id': x['id'], 'scan': s, 'rank': rank, 'source_channel': x['source_channel'],
                       'frequency_hz': x['frequency_hz'], 'width': x['width_channels'], 'contrast': x['contrast']}
            if (rec['width'] not in [1, 3] or rec['source_channel'] - C0 - H < 0
                    or rec['source_channel'] - C0 + H >= N):
                raise ValueError('Panel geometry mismatch')
            records.append(rec)
    reused = {}
    for entry in read(root, cfg['original_time_review']):
        x = entry['selected_profile']
        reused[x['ranked_id']] = {'source_channel': x['source_channel'], 'width': x['winning_width_channels'],
                                'source': 'saved_original_seven_TIME_REVIEW',
                                'by_scan': {s: {'residual_each_row': m['center_minus_flank_each_row'],
                                                'positive_rows': m['positive_center_minus_flank_rows'],
                                                'mean_residual': m['mean_center_minus_flank'],
                                                'median_residual': m['median_center_minus_flank']}
                                            for s, m in entry['scan_measurements'].items()}}
    for x in read(root, cfg['reciprocal_time_review']):
        reused[x['id']] = {'source_channel': x['source_channel'], 'width': x['width_channels'],
                           'source': 'saved_nine_reciprocal_CONTROL_TIME_REVIEW', 'by_scan': x['by_scan']}
    fresh = [x for x in records if x['id'] not in reused]
    if len(records) != 120 or len(reused) != 16 or len(fresh) != 104 or len(set(x['id'] for x in records)) != 120:
        raise ValueError('Panel cardinality or identities mismatch')
    for x in records:
        if x['id'] in reused:
            old = reused[x['id']]
            if old['source_channel'] != x['source_channel'] or old['width'] != x['width']:
                raise ValueError('Reused profile identity/width mismatch')
    raw = np.empty((104, 6, R, 2 * H + 1), dtype=np.float32)
    for j, s in enumerate(SCANS):
        with h5py.File(Path(a.cache_dir) / f'{s}.compact.h5', 'r', rdcc_nbytes=80 * 1024**2, rdcc_nslots=521, rdcc_w0=0.0) as f:
            data = f['data']
            if data.shape != (R, 1, N) or data.dtype != np.dtype('float32') or data.chunks != (1, 1, N):
                raise ValueError('Preserved native power dimensions mismatch')
            for i, x in enumerate(fresh):
                k = x['source_channel'] - C0
                raw[i, j] = data[:, 0, k - H:k + H + 1]
        print('NEW_RANKED_PANEL_PATCHES_READ', s, len(fresh), flush=True)
    if not np.isfinite(raw).all() or (raw < 0).any():
        raise ValueError('Invalid new native panel powers')
    meds = read(root, cfg['normalization'])['row_medians_over_full_physical_chunk']
    medians = np.asarray([meds[s] for s in SCANS], dtype=np.float64)
    if medians.shape != (6, R) or not np.isfinite(medians).all() or (medians <= 0).any():
        raise ValueError('Invalid preserved row medians')
    norm = raw / medians[None, :, :, None]
    bg = np.median(norm[:, :, :, np.abs(np.arange(-H, H + 1)) > 3], axis=-1)
    residuals = np.empty((104, 6, R), dtype=np.float64)
    for i, x in enumerate(fresh):
        h = x['width'] // 2
        residuals[i] = norm[i, :, :, H-h:H+h+1].mean(axis=-1) - bg[i]
        reused[x['id']] = {'source_channel': x['source_channel'], 'width': x['width'], 'source': 'new_fixed_ranked_panel',
                           'by_scan': {s: {'residual_each_row': residuals[i, j].tolist(),
                                          'positive_rows': int((residuals[i, j] > 0).sum()),
                                          'mean_residual': float(residuals[i, j].mean()),
                                          'median_residual': float(np.median(residuals[i, j]))} for j, s in enumerate(SCANS)}}
    joined = []
    for x in records:
        m = reused[x['id']]
        joined.append({**x, 'adjacent_control_count': COUNTS[x['scan']], 'measurement_source': m['source'], 'by_scan': m['by_scan']})
    by_scan, by_matched_count = {}, {}
    for s in SCANS:
        xs = [x for x in joined if x['scan'] == s]
        vals = [x['by_scan'][s]['positive_rows'] for x in xs]
        by_scan[s] = {'ranked_profiles': len(xs), 'adjacent_control_count': COUNTS[s],
                      'width_counts': {str(w): sum(x['width'] == w for x in xs) for w in (1, 3)},
                      'positive_rows_histogram_0_to_16': [vals.count(k) for k in range(17)],
                      'at_least_13_positive_rows': sum(k >= 13 for k in vals),
                      'at_least_15_positive_rows': sum(k >= 15 for k in vals),
                      'all_16_positive_rows': vals.count(16)}
    for count in (1, 2):
        block = {}
        for role in ('on', 'off'):
            xs = [x for x in joined if x['scan'].endswith('_' + role) and COUNTS[x['scan']] == count]
            vals = [x['by_scan'][x['scan']]['positive_rows'] for x in xs]
            block[role] = {'profiles': len(xs), 'at_least_13_positive_rows': sum(k >= 13 for k in vals),
                           'at_least_15_positive_rows': sum(k >= 15 for k in vals), 'all_16_positive_rows': vals.count(16)}
        by_matched_count[str(count)] = block
    np.savez_compressed(out / 'new_104_fixed_patches.npz', raw_power=raw, row_normalized_power=norm,
                        residual_each_row=residuals, saved_row_medians=medians,
                        profile_ids=np.asarray([x['id'] for x in fresh]),
                        source_channels=np.asarray([x['source_channel'] for x in fresh]),
                        selected_widths=np.asarray([x['width'] for x in fresh]), scan_labels=np.asarray(SCANS))
    dump(out / 'ALL_120_TIME_PROFILES.json', joined)
    result = {'status': 'COMPLETE_FIXED_TOP20_PER_SCAN_NATIVE_TIME_PANEL', 'profiles': 120,
              'reused_profiles_without_remeasurement': 16, 'new_profiles_measured': 104,
              'raw_power_values_newly_retained': int(raw.size), 'by_scan': by_scan, 'by_matched_control_count': by_matched_count,
              'all_16_profiles': [{k: x[k] for k in ['id', 'scan', 'rank', 'frequency_hz', 'width']} for x in joined
                                  if x['by_scan'][x['scan']]['positive_rows'] == 16],
              'calibrated_probability': False, 'independent_visits': 1, 'new_observing_exposure_s': 0,
              'same_existing_selection_family': True, 'all_ranked_profiles_retained': True,
              'original_seven_dispositions': 'UNRESOLVED_UNCHANGED', 'A_B': 'FAIL_CLOSED_UNCHANGED',
              'limitations': ['Data-selected ranks from the same visit; neither profiles nor row signs are independent trials',
                              'Native OFF includes known interference and other possible backgrounds; no certified null or exchangeability',
                              'Whole ranking family preserved, but this is descriptive control comparison, not a significance calibration',
                              'Selected width1/3 is used for the center; fixed flanks exclude offsets ±0…3; no frequency/time optimization',
                              'Previously known control lines are retained; their presence is not a newly discovered event',
                              'A control feature at another frequency does not veto an original ON feature']}
    dump(out / 'RANKED_TIME_PANEL_RESULT.json', result)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    for ax, count in zip(axes, (1, 2)):
        block = by_matched_count[str(count)]
        keys = ['at_least_13_positive_rows', 'at_least_15_positive_rows', 'all_16_positive_rows']
        xx = np.arange(3)
        for role, offset, color, label in [('on', -.18, '#1763a6', 'Original ON'), ('off', .18, '#b46116', 'Reciprocal OFF')]:
            ax.bar(xx + offset, [block[role][k] for k in keys], width=.36, color=color,
                   label=label + f' (n={block[role]["profiles"]})')
        ax.set_xticks(xx, ['≥13 / 16', '≥15 / 16', '16 / 16']); ax.set_ylabel('Selected profiles')
        ax.set_title(f'{count} adjacent control scan(s)\nAll top20 ranks per included scan'); ax.legend(fontsize=9)
        ax.grid(axis='y', alpha=.2)
    fig.suptitle('Fixed ranked-panel time persistence — same native visit, no calibrated probability', fontsize=11)
    fig.savefig(out / 'ranked_time_panel_overview.png', dpi=150); plt.close(fig)
    outputs = [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(out.iterdir()) if p.is_file()]
    receipt = {'status': result['status'], 'script_sha256': sha(__file__), 'scope_sha256': sha(a.scope),
               'verified_inputs': cfg['inputs'], 'outputs': outputs, 'new_profiles': 104, 'reused_profiles': 16,
               'new_raw_power_values': int(raw.size), 'new_telescope_GETs': 0, 'new_source_bytes': 0,
               'new_drift_or_stationary_contrast_searches': 0, 'process_CPU_s_including_imports': time.process_time(),
               'wall_s_including_imports': time.monotonic() - START, 'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
               'whole_activity_CPU_s': None, 'conservative_activity_reservation_CPU_s': 100}
    dump(out / 'ANALYSIS_RECEIPT.json', receipt)
    print(json.dumps({k: receipt[k] for k in ['status', 'process_CPU_s_including_imports', 'wall_s_including_imports', 'peak_RSS_bytes']}), flush=True)


if __name__ == '__main__':
    START = time.monotonic()
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('scope', 'workspace', 'cache-dir', 'outdir'):
        p.add_argument('--' + key, required=True)
    a = p.parse_args(); Path(a.outdir).mkdir(parents=True, exist_ok=False)
    def deadline(signum, frame):
        raise TimeoutError('Frozen ranked panel cap reached')
    signal.signal(signal.SIGALRM, deadline); signal.signal(signal.SIGXCPU, deadline)
    signal.alarm(240); resource.setrlimit(resource.RLIMIT_CPU, (90, 91))
    resource.setrlimit(resource.RLIMIT_AS, (1610612736, 1610612736))
    try:
        import numpy as np
        import h5py
        import hdf5plugin
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        main(a)
    except BaseException as exc:
        dump(Path(a.outdir) / 'FAILURE.json', {'status': 'FAILED_CLOSED_RANKED_TIME_PANEL', 'error_type': type(exc).__name__,
                                             'error': str(exc), 'process_CPU_s': time.process_time(),
                                             'wall_s': time.monotonic() - START, 'retry_authorized': False})
        raise
    finally:
        signal.alarm(0)
