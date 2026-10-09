"""Display two saved triage flags; no new source requests or detector scores."""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import time

for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
resource.setrlimit(resource.RLIMIT_CPU, (60, 65))
resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
import numpy as np
import h5py
import hdf5plugin
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/radio_quicklook_20261009'
SOURCE0 = 159383552
GROUPS = ('epoch1_on_contiguous_0006', 'epoch1_on_contiguous_0094')


def read(path):
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def main():
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Saved-display wall bound')))
    signal.alarm(120)
    out = BASE / 'flagged_review'
    out.mkdir(exist_ok=False)
    source, source_hash = read(ROOT / 'pilot_source_20261008/primary/source_manifest.json')
    triage, triage_hash = read(BASE / 'SIGNAL_TRIAGE.json')
    norm, norm_hash = read(BASE / 'broad_inventory/normalization.json')
    broad, broad_hash = read(BASE / 'broad_inventory/BROAD_INVENTORY_RECEIPT.json')
    if (source_hash != '6a9c166f15de69c378e3346fcd5dac1082790345622b2df3af674f108bf29aec'
            or triage['status'] != 'COMPLETED_SAVED_MAXIMA_DESCRIPTIVE_TRIAGE'
            or set(triage['manual_review_flagged_group_ids']) != set(GROUPS)):
        raise ValueError('Expected complete saved evidence and exactly two manual flags')
    groups = [next(g for g in triage['groups'] if g['group_id'] == group_id) for group_id in GROUPS]
    samples, reads = {}, []
    for item in source['sources']:
        label = item['label']
        samples[label] = {}
        # One local open per scan; 80MiB cache can retain all16 decoded chunks
        # across both narrow slices. No HTTP or raw source file is opened.
        with h5py.File(BASE / 'arrays' / (label + '.compact.h5'), 'r', rdcc_nbytes=80 * 1024**2) as f:
            data = f['data']
            if (data.shape != (16, 1, 1048576) or data.dtype != np.dtype('<f4')
                    or data.attrs['original_source_url'] != item['url']
                    or data.attrs['original_source_etag'] != item['etag']):
                raise ValueError('Cached source geometry/identity differs')
            for g in groups:
                lo, hi = g['ON_trajectory_interval_plus32_channels_half_open']
                raw = np.asarray(data[:, 0, lo - SOURCE0:hi - SOURCE0], dtype='<f4')
                if raw.shape != (16, hi - lo) or not np.isfinite(raw).all() or (raw < 0).any():
                    raise ValueError('Invalid complete display slice')
                samples[label][g['group_id']] = raw
                reads.append({'scan_id': label, 'group_id': g['group_id'], 'selected_source_interval_half_open': [lo, hi],
                              'application_powers_read': int(raw.size), 'raw_slice_sha256': hashlib.sha256(raw.tobytes()).hexdigest()})
    anchor = source['sources'][0]['current_header']['data_attributes']['tstart']
    for g in groups:
        fig, axes = plt.subplots(3, 2, figsize=(12, 10), constrained_layout=True)
        lo, hi = g['ON_trajectory_interval_plus32_channels_half_open']
        p = g['representative']
        ref_header = next(s for s in source['sources'] if s['label'] == g['scan_id'])['current_header']['data_attributes']
        reference = (ref_header['tstart'] - anchor) * 86400 + .5 * ref_header['tsamp']
        for ax, item in zip(axes.flat, source['sources']):
            label, h = item['label'], item['current_header']['data_attributes']
            levels = np.asarray(norm['row_medians_over_full_physical_chunk'][label])
            shown = samples[label][g['group_id']] / levels[:, None]
            t0 = (h['tstart'] - anchor) * 86400
            f0, f1 = (h['fch1'] + h['foff'] * (j - .5) for j in (lo, hi))
            im = ax.imshow(shown, origin='lower', aspect='auto', interpolation='nearest',
                           extent=[f0, f1, t0, t0 + 16 * h['tsamp']], vmin=.6, vmax=1.6, cmap='magma')
            mids = t0 + (np.arange(16) + .5) * h['tsamp']
            predicted = (p['frequency_hz_at_first_midpoint'] + p['winning_drift_hz_s'] * (mids - reference)) / 1e6
            ax.plot(predicted, mids, color='cyan', linewidth=.8, label='Saved ON track extrapolation')
            ax.set_title(f"{label} ({item['role'].upper()})", fontsize=10)
            ax.set_xlabel('Frequency (MHz)')
            ax.ticklabel_format(axis='x', useOffset=False, style='plain')
            ax.set_ylabel('Seconds from MJD anchor')
        axes.flat[0].legend(fontsize=7, loc='upper left')
        fig.colorbar(im, ax=list(axes.flat), label='Raw cached power / saved full-chunk row median; shared clipped scale')
        fig.suptitle(g['group_id'] + '\nManual flag display; no detector scoring, classification or OFF veto')
        fig.savefig(out / (g['group_id'] + '.png'), dpi=115)
        plt.close(fig)
    comments = {
        GROUPS[0]: 'Saved ON zero-drift projection7.0576; OFF7.3801/5.8369/9.0413 at nearly the same frequency. OFF response is present despite all OFF values being below descriptive10.',
        GROUPS[1]: 'Saved ON zero-drift projection9.1297; immediately following OFF9.3942 at exactly the same channel. Other OFF6.1158/8.3386. This is not evidence of OFF absence.'}
    record = {'status': 'COMPLETED_TWO_SAVED_FLAG_DISPLAYS_PENDING_VISUAL_INTERPRETATION',
              'source_manifest_sha256': source_hash, 'triage_sha256': triage_hash, 'broad_receipt_sha256': broad_hash,
              'saved_row_normalization_sha256': norm_hash, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'original_compact_file_sha256_from_prior_receipt_not_rehashed_here': broad['original_compact_file_sha256'],
              'selection': 'Exactly the two saved all-three-OFF-zero-drift-projection-below10 flags; fixed ON swept-channel interval plus32, all16rows/all6scans',
              'display_only_row_normalization': 'Existing full-chunk row medians; no new preprocessing statistic',
              'read_slices': reads, 'groups': [{'group_id': g['group_id'], 'existing_saved_evidence_observation': comments[g['group_id']],
                                            'representative': g['representative'], 'plot': g['group_id'] + '.png'} for g in groups],
              'new_GETs': 0, 'new_external_bytes': 0, 'new_detector_scores': 0,
              'local_HDF5_decode': 'Narrow cached hyperslabs; HDF5 may transparently decode intersecting complete physical chunks; this is display, not a new source acquisition',
              'limitations': ['The optimized box-track score and collapsed zero-drift residual have different statistics and cannot share a calibrated threshold',
                              'Below10 is not OFF absence; displayed ON/OFF morphology does not establish an interference or celestial origin',
                              'Only two selected groups and widths1/3 linear tracks; no calibrated FAP, sensitivity or qualified sky-null inference',
                              'All6scans are one historical visit'],
              'CPU_seconds_including_imports': time.process_time(), 'wall_seconds_after_imports': time.monotonic() - started,
              'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    with (out / 'REVIEW.json').open('x') as f:
        json.dump(record, f, indent=2, allow_nan=False)
        f.write('\n')
    signal.alarm(0)
    print(json.dumps({'status': record['status'], 'CPU_seconds': record['CPU_seconds_including_imports'], 'groups': GROUPS}))


if __name__ == '__main__':
    main()
