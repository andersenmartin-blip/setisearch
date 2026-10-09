#!/usr/bin/env python3
"""Fixed descriptive frequency shapes; no search, significance or classification."""
import argparse
import csv
import hashlib
import io
import json
import resource
import signal
import time
import zipfile
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(args):
    scope = json.loads(Path(args.scope).read_text())
    assert sha(Path(__file__).read_bytes()) == scope['script_sha256'], 'script freeze mismatch'
    assert sha(Path(args.reference).read_bytes()) == scope['original_reference_sha256'], 'reference freeze mismatch'
    reference = {x['id']: x for x in json.loads(Path(args.reference).read_text())}
    signal.signal(signal.SIGALRM, lambda signum, frame: (_ for _ in ()).throw(TimeoutError('wall limit')))
    signal.alarm(scope['limits']['job_wall_s'])
    resource.setrlimit(resource.RLIMIT_CPU, (scope['limits']['job_CPU_s'], scope['limits']['job_CPU_s']))
    resource.setrlimit(resource.RLIMIT_AS, (scope['limits']['job_memory_bytes'], scope['limits']['job_memory_bytes']))
    cpu0, wall0 = time.process_time(), time.monotonic()
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    archive = Path(args.archive)
    digest = hashlib.sha256()
    with archive.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024*1024), b''):
            digest.update(chunk)
    assert archive.stat().st_size == scope['input_archive']['bytes']
    assert digest.hexdigest() == scope['input_archive']['sha256'], 'archive identity mismatch'
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    offsets = np.arange(-64, 65)
    scans = scope['scans']
    results, profiles, input_checks = [], [], []
    with zipfile.ZipFile(archive) as z:
        for item in scope['inputs']:
            names = [n for n in z.namelist() if Path(n).name == item['path']]
            assert len(names) == 1, ('ambiguous patch', item['id'])
            rawbytes = z.read(names[0])
            assert len(rawbytes) == item['bytes'] and sha(rawbytes) == item['sha256']
            with np.load(io.BytesIO(rawbytes), allow_pickle=False) as data:
                norm = data['row_normalized_power']
                raw = data['raw_power']
                baseline = data['fixed_flank_median_row_normalized_power']
                old_residual = data['center_minus_flank_each_row']
                assert norm.shape == (6,16,129) and raw.shape == (6,16,129)
                assert baseline.shape == (6,16)
                assert data['scans'].tolist() == scans
                assert int(data['source_channel']) == item['source_channel']
                assert str(data['originating_on'].item()) == item['originating_on']
                assert int(data['width_channels']) == 1
                assert np.array_equal(data['source_channel_offsets'], offsets)
                for key in ['df_hz','tsamp_s','fch1_hz']:
                    assert float(data[key]) == scope[key], ('grid mismatch', key)
                np.testing.assert_array_equal(data['frequency_offsets_hz'], offsets*scope['df_hz'])
                assert abs((scope['fch1_hz'] + item['source_channel']*scope['df_hz'])/1e6 - item['frequency_mhz']) < 1e-9
                assert np.isfinite(norm).all() and np.isfinite(baseline).all()
                # Verify the saved normalization identity; do not recompute its medians.
                np.testing.assert_array_equal(norm, raw.astype(np.float64) / data['saved_full_chunk_row_medians'][:,:,None])
                residual = norm - baseline[:,:,None]
                np.testing.assert_array_equal(residual[:,:,64], old_residual)
                for i, s in enumerate(scans):
                    prior = reference[item['id']]['scans'][s]
                    assert sha(np.asarray(raw[i], dtype='<f4').tobytes(order='C')) == prior['raw_slice_sha256']
                    np.testing.assert_array_equal(old_residual[i], np.array(prior['center_minus_flank_each_row']))
                profile = residual.mean(axis=1)
                freq_offset = data['frequency_offsets_hz'].copy()
            measures = {}
            for i, s in enumerate(scans):
                windows = {str(w): float(profile[i,64-w//2:65+w//2].mean()) for w in scope['widths_channels']}
                # Round-off from axis reduction is expected, bounded against the old means.
                assert abs(windows['1'] - reference[item['id']]['scans'][s]['mean_center_minus_flank']) < 1e-14
                neighbor = float((profile[i,63] + profile[i,65])/2)
                measures[s] = {'fixed_window_mean': windows, 'immediate_neighbor_mean': neighbor,
                               'central_minus_immediate_neighbors': windows['1']-neighbor}
            origin = item['originating_on']
            adjacent = scope['adjacency'][origin]
            differences = {str(w): measures[origin]['fixed_window_mean'][str(w)] - max(measures[s]['fixed_window_mean'][str(w)] for s in adjacent) for w in scope['widths_channels']}
            results.append({'id':item['id'], 'originating_on':origin, 'source_channel':item['source_channel'],
                            'frequency_mhz':item['frequency_mhz'], 'adjacent_OFF':adjacent,
                            'scans':measures, 'fixed_center_ON_minus_max_adjacent_OFF_window_mean':differences,
                            'classification':'UNRESOLVED_UNCHANGED'})
            profiles.append(profile)
            input_checks.append({'id':item['id'],'archive_member':names[0],'sha256':sha(rawbytes),
                                 'bytes':len(rawbytes),'raw_six_scans_verified':True,
                                 'saved_normalization_identity_verified':True,'old_all16_center_residuals_verified':True})
    profiles = np.asarray(profiles)
    np.savez_compressed(out/'FIXED_FREQUENCY_PROFILES.npz', ids=np.array([x['id'] for x in results]),
                        scans=np.array(scans), source_channel_offsets=offsets, frequency_offsets_hz=freq_offset,
                        mean_saved_row_normalized_minus_saved_flank=profiles)
    with (out/'FIXED_FREQUENCY_PROFILES.csv').open('w',newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['id','source_channel_offset','frequency_offset_hz'] + scans)
        for k, item in enumerate(results):
            for j, off in enumerate(offsets):
                w.writerow([item['id'],int(off),float(freq_offset[j])] + profiles[k,:,j].tolist())
    fig, axes = plt.subplots(4,2,figsize=(12,12),sharex=True,sharey=True,layout='constrained')
    shown = np.abs(offsets) <= 16
    x = freq_offset[shown]
    order = np.argsort(x)
    colors = {'epoch1_on':'#777777','epoch1_off':'#e69f00','epoch2_on':'#777777',
              'epoch2_off':'#8b5cf6','epoch3_on':'#777777','epoch3_off':'#009e73'}
    for k, (ax,item) in enumerate(zip(axes.flat,results)):
        origin, adj = item['originating_on'], item['adjacent_OFF']
        for i,s in enumerate(scans):
            if s == origin:
                ax.plot(x[order],profiles[k,i,shown][order],'-o',color='#0072b2',markersize=3,linewidth=1.5,label='originating '+s)
            elif s in adj:
                ax.plot(x[order],profiles[k,i,shown][order],'-',color=colors[s],linewidth=1,label=s)
            else:
                ax.plot(x[order],profiles[k,i,shown][order],'-',color='#888888',alpha=.30,linewidth=.65,label='other scans' if s == next(t for t in scans if t != origin and t not in adj) else None)
        ax.axhline(0,color='#444444',linewidth=.6)
        ax.axvline(0,color='#444444',linewidth=.6,linestyle=':')
        ax.set_title(item['id']+'\n'+f"{item['frequency_mhz']:.6f} MHz",fontsize=10)
        ax.grid(alpha=.15)
        ax.legend(fontsize=7,loc='upper right')
    axes.flat[-1].axis('off')
    axes.flat[-1].text(0,.95,'Fixed centers and all 16 time rows\n\nBlue: originally selected ON\nColored: adjacent OFF at same frequency\nGray: remaining scans\n\nOne visit: 2016-03-17\nDescriptive, post-selection\nNo significance or classification\n\nFull offsets -64..64 and all six scans\nare retained in the data files.',ha='left',va='top',transform=axes.flat[-1].transAxes,fontsize=11)
    fig.supxlabel('Frequency offset from fixed center (Hz)')
    fig.supylabel('Mean saved row-normalized power minus saved flank median')
    fig.suptitle('Seven preselected weak profiles: fixed frequency shape',fontsize=15)
    fig.savefig(out/'FIXED_FREQUENCY_SHAPES.png',dpi=150)
    plt.close(fig)
    summary={'scope':'POST_DATA_DESCRIPTIVE_FIXED_FREQUENCY_SHAPE_ONLY',
             'scope_sha256':sha(Path(args.scope).read_bytes()),'script_sha256':sha(Path(__file__).read_bytes()),
             'reference_sha256':sha(Path(args.reference).read_bytes()),'archive_verified':True,
             'input_checks':input_checks,'records':results,'scans_evaluated':42,'fixed_windows_per_scan':5,
             'new_observations':0,'new_telescope_power_bytes':0,'A_B':'FAIL_CLOSED_UNCHANGED',
             'classification':'ALL_SEVEN_UNRESOLVED_UNCHANGED','limitations':scope['limitations']}
    (out/'FREQUENCY_SHAPE_RESULT.json').write_text(json.dumps(summary,indent=2)+'\n')
    receipt={'process_CPU_s':time.process_time()-cpu0,'wall_s':time.monotonic()-wall0,
             'maxrss_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             'success':True,'new_telescope_HTTP_requests':0,'all_inputs_verified':True,
             'files':{p.name:{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()}}
    (out/'EXECUTION_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    signal.alarm(0)
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--scope',required=True)
    parser.add_argument('--reference',required=True)
    parser.add_argument('--archive',required=True)
    parser.add_argument('--output',required=True)
    run(parser.parse_args())
